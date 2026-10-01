# -*- coding: utf-8 -*-
"""
喜鹊儿（青果教务 KINGOSOFT）课表同步服务。

- 登录协议：CAS 登录 + 动态度密钥 DES 加密参数（参考开源实现 XiQueEr2Ics，协议逻辑已重写）
- 课表接口：/student/wsxk.xskcb10319.jsp?params=base64(xn=学年&xq=学期&xh=学号)
- 解析：table#mytable 的 HTML 结构（bs4）
- 落库：按学号定位 User -> class_group_id，将个人课表写入 courses（班级维度、幂等更新）

密码安全：本地只保存 md5(明文密码)（再经系统加密存储），登录时使用该 MD5，
与青果前端“密码先 MD5 一次再拼盐二次 MD5”的口令流程一致，绝不落库明文。
"""

import base64
import hashlib
import re
import threading
from dataclasses import dataclass, field

import requests

from app.services.kingo_des import KingoDES

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def xq_to_semester(school_year: int, xq: int) -> str:
    """喜鹊儿学年学期 -> 本地学期串。xq: 0=第一学期, 1=第二学期"""
    xq = 1 if int(xq) == 0 else 2
    return f"{school_year}-{school_year + 1}-{xq}"


def semester_to_xq(semester: str):
    """本地学期串 -> (学年起始年, xq)。如 "2026-2027-1" -> (2026, 0)"""
    parts = semester.strip().split("-")
    try:
        year = int(parts[0])
        num = int(parts[-1])
    except (ValueError, IndexError):
        raise ValueError(f"无法解析学期格式: {semester}")
    xq = 0 if num == 1 else 1
    return year, xq


class XqeLoginError(Exception):
    """喜鹊儿登录失败"""


class XqeNetworkError(Exception):
    """网络/超时错误"""


class XqeParseError(Exception):
    """课表解析失败"""


class XqeClient:
    """喜鹊儿（青果教务）客户端：登录 + 课表拉取。

    使用 threading.local 保存每线程独立的 requests.Session，
    避免 FastAPI 线程池中 Session 串用 cookie。
    """

    # 各请求间的必要间隔，避免被教务系统风控（参考开源项目建议 0.2s）
    REQUEST_INTERVAL = 0.2

    def __init__(self, base_url: str, timeout: int = 8):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._local = threading.local()

    # ---------------- 会话管理 ----------------
    @property
    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            })
            self._local.session = s
        return s

    def _get(self, url: str, **kwargs) -> requests.Response:
        import time
        last = getattr(self._local, "last_request", 0.0)
        gap = self.REQUEST_INTERVAL - (time.monotonic() - last)
        if gap > 0:
            time.sleep(gap)
        try:
            resp = self._session.get(url, timeout=self.timeout, **kwargs)
        except requests.RequestException as e:
            raise XqeNetworkError(f"请求失败: {e}")
        self._local.last_request = time.monotonic()
        return resp

    def _post(self, url: str, data=None, headers=None) -> requests.Response:
        import time
        last = getattr(self._local, "last_request", 0.0)
        gap = self.REQUEST_INTERVAL - (time.monotonic() - last)
        if gap > 0:
            time.sleep(gap)
        try:
            resp = self._session.post(url, data=data, headers=headers, timeout=self.timeout)
        except requests.RequestException as e:
            raise XqeNetworkError(f"请求失败: {e}")
        self._local.last_request = time.monotonic()
        return resp

    # ---------------- 登录 ----------------
    def login(self, username: str, once_md5_password: str) -> None:
        """登录喜鹊儿。

        Args:
            username: 学号
            once_md5_password: 已做一次 MD5 的密码（与青果前端 md5(password) 一致）
        """
        base = self.base_url
        session = self._session

        # 1. 访问登录页，取 JSESSIONID 与 _sessionid
        try:
            resp = session.get(
                f"{base}/cas/login.action",
                timeout=self.timeout,
                allow_redirects=True,
            )
        except requests.RequestException as e:
            raise XqeNetworkError(f"无法访问教务登录页: {e}")

        session_id_match = re.search(r'var\s+_sessionid\s*=\s*"([A-F0-9]+)"', resp.text)
        if not session_id_match:
            raise XqeLoginError("登录页未返回 _sessionid，请确认教务地址正确（需为青果教务系统）")
        session_id = session_id_match.group(1)
        jsessionid = session.cookies.get("JSESSIONID", "")

        # 2. 获取临时 DES 密钥与服务器时间
        deskey = self._get(f"{base}/frame/homepage?method=getTempDeskey").text.strip()
        if not deskey:
            raise XqeLoginError("获取 DES 密钥失败")
        nowtime = self._get(f"{base}/frame/homepage?method=getTempNowtime").text.strip()
        if not nowtime:
            raise XqeLoginError("获取服务器时间失败")

        # 3. 构造加密登录参数（协议与青果前端 jkingo.des 一致）
        params_u = base64.b64encode(f"{username};;{session_id}".encode()).decode()
        params_p = md5_hex(once_md5_password + md5_hex(""))
        params_v1 = (
            f"_u={params_u}&_p={params_p}&randnumber=&isPasswordPolicy=1"
            f"&txt_mm_expression=14&txt_mm_length=15&txt_mm_userzh=0"
            f"&hid_flag=1&hidlag=1&hid_dxyzm="
        )
        token = md5_hex(md5_hex(params_v1) + md5_hex(nowtime))
        payload = (
            f"params={KingoDES.encrypt(params_v1, deskey)}"
            f"&token={token}&timestamp={nowtime}&deskey={deskey}&ssessionid={session_id}"
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": f"{base}/cas/login.action",
            "Cookie": f"JSESSIONID={jsessionid}",
        }
        login_resp = self._post(f"{base}/cas/logon.action", data=payload, headers=headers)

        try:
            data = login_resp.json()
        except ValueError:
            raise XqeLoginError("登录响应异常（非 JSON），请检查教务地址或账号密码")
        if str(data.get("status")) != "200":
            msg = str(data.get("msg") or data.get("message") or "登录失败")
            raise XqeLoginError(f"登录失败：{msg}")
        self._local.session_id = session_id

    # ---------------- 课表 ----------------
    def get_timetable(self, school_year: int, term: int, user_code: str) -> str:
        """拉取个人课表 HTML。

        Args:
            school_year: 学年起始年，如 2026（对应 2026-2027 学年）
            term: 0=第一学期, 1=第二学期
            user_code: 学号
        """
        params_encoded = base64.b64encode(
            f"xn={school_year}&xq={term}&xh={user_code}".encode()
        ).decode()
        url = f"{self.base_url}/student/wsxk.xskcb10319.jsp?params={params_encoded}"
        resp = self._get(
            url,
            headers={
                "Referer": f"{self.base_url}/student/xkjg.wdkb.jsp?menucode=S20301",
            },
        )
        if "未登录" in resp.text or "login" in resp.text[:500].lower():
            raise XqeLoginError("会话已失效，请重新登录")
        return resp.text


# ==================== HTML 解析 ====================

_WEEK_RANGE_RE = re.compile(r"(\d+)\s*[-~至到－]\s*(\d+)\s*周")
_WEEK_SINGLE_RE = re.compile(r"(?<![-\d])(\d+)\s*周")
_PERIOD_RANGE_RE = re.compile(r"(\d+)\s*[-~至到－]\s*(\d+)\s*节")
_PERIOD_SINGLE_RE = re.compile(r"(?<![-\d])(\d+)\s*节")


def _parse_ranges(text: str, range_re, single_re):
    """从文本中提取数字区间集合，返回 (min, max)。如 '1-16周（单周）' -> (1, 16)"""
    values: list[int] = []
    for m in range_re.finditer(text):
        values.append(int(m.group(1)))
        values.append(int(m.group(2)))
    if not values:
        for m in single_re.finditer(text):
            values.append(int(m.group(1)))
    if not values:
        return None, None
    return min(values), max(values)


def _find_bolder_font(div):
    """兼容多种 font style 写法找到课程名元素"""
    f = div.find("font", style="font-weight: bolder")
    if f:
        return f
    for font in div.find_all("font"):
        style = (font.get("style") or "").replace(" ", "")
        if "font-weight:bolder" in style or "font-weight:bolder;" in style:
            return font
    return None


def _div_is_course(div) -> bool:
    style = (div.get("style") or "").replace(" ", "")
    return "padding-bottom:5px;clear:both;" in style or "clear:both" in style


def parse_course_schedule(html: str) -> list[dict]:
    """解析喜鹊儿课表 HTML -> 课程列表。

    每项:
        weekday: 1-7
        title: 课程名
        teacher: 授课教师
        week_start / week_end: 周次区间
        start_period / end_period: 节次区间
        location: 上课地点
    """
    if BeautifulSoup is None:
        raise XqeParseError("缺少 beautifulsoup4 依赖，请安装后重试")
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": "mytable"})
    if table is None:
        raise XqeParseError("课表页面未找到 table#mytable，可能学期无课表或页面结构变化")

    courses: list[dict] = []
    for row in table.find_all("tr"):
        tds_all = row.find_all("td", recursive=False)
        if not tds_all:
            continue

        # 跳过含 td1（节次标签列）的行之外，先看是否表头行
        row_text = row.get_text(strip=True)
        if any(day in row_text for day in WEEKDAY_CN) and len(row_text) < 40:
            continue

        # 去掉开头的 td1 标签列
        cells = [td for td in tds_all if "td1" not in (td.get("class") or [])]
        cells = cells[:7]
        if not cells:
            continue

        for day_idx, cell in enumerate(cells):
            for div in cell.find_all("div", recursive=False):
                if not _div_is_course(div):
                    continue
                title_font = _find_bolder_font(div)
                if title_font is None:
                    continue
                title = title_font.get_text(strip=True)
                if not title:
                    continue

                # 文本行（HTML 内部无点号分隔，用 | 连接再拆分）
                lines = [l.strip() for l in div.get_text(separator="|").split("|") if l.strip()]
                teacher = ""
                week_text = ""
                location = ""
                for line in lines:
                    if "教师" in line:
                        teacher = line.replace("教师:", "").replace("教师：", "").strip()
                    elif ("周" in line and "节" in line) or (re.search(r"\[\s*\d", line)):
                        week_text = line
                    elif "节" in line and re.search(r"周", line):
                        week_text = line
                # 地点：不带 周/节 的最后一行文本
                for line in reversed(lines):
                    if "周" not in line and "节" not in line and "教师" not in line and line != title:
                        location = line
                        break

                week_start, week_end = _parse_ranges(week_text, _WEEK_RANGE_RE, _WEEK_SINGLE_RE)
                if week_start is None:
                    week_start, week_end = 1, 1  # 未标注周次时默认第 1 周
                start_period, end_period = _parse_ranges(
                    week_text or line, _PERIOD_RANGE_RE, _PERIOD_SINGLE_RE
                )
                if start_period is None:
                    start_period, end_period = 1, 2

                courses.append({
                    "weekday": day_idx + 1,
                    "title": title,
                    "teacher": teacher or "未知",
                    "week_start": week_start,
                    "week_end": week_end,
                    "start_period": start_period,
                    "end_period": end_period,
                    "location": location or "待定",
                })
    return courses


# ==================== 落库 ====================

@dataclass
class XqeSyncResult:
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list = field(default_factory=list)
    semester: str = ""
    class_name: str = ""
    student_name: str = ""


def sync_timetable(
    db,
    root_url: str,
    username: str,
    once_md5_password: str,
    school_year: int,
    term: int,
) -> XqeSyncResult:
    """登录喜鹊儿拉取课表并同步到本地 Course 表。

    Args:
        db: SQLAlchemy Session
        root_url: 教务系统根地址
        username: 学号
        once_md5_password: 已 md5 一次的密码（保存时即应存此形态）
        school_year: 学年起始年
        term: 0/1
    """
    from app.models.academic import ClassGroup, Course
    from app.models.user import User

    result = XqeSyncResult()
    semester = xq_to_semester(school_year, term)
    result.semester = semester

    # 1. 定位学生与班级
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise XqeLoginError(f"系统中不存在学号「{username}」对应的用户，请先在学生管理中创建")
    if not user.class_group_id:
        raise XqeLoginError(f"学生「{user.name}」未关联班级，无法确定课表归属班级")
    cg = db.query(ClassGroup).get(user.class_group_id)
    if cg is None:
        raise XqeLoginError("学生关联的班级不存在，请重新设置")
    result.class_name = cg.name
    result.student_name = user.name

    # 2. 登录 + 拉取
    client = XqeClient(root_url)
    client.login(username, once_md5_password)
    html = client.get_timetable(school_year, term, username)
    parsed = parse_course_schedule(html)
    if not parsed:
        raise XqeParseError("课表解析结果为空（可能该学期无课表）")

    # 3. 幂等写库（同班同名同日同时段视为同一条，更新其它字段）
    for item in parsed:
        result.total += 1
        dup = db.query(Course).filter(
            Course.class_group_id == cg.id,
            Course.semester == semester,
            Course.name == item["title"],
            Course.day_of_week == item["weekday"],
            Course.start_period == item["start_period"],
        ).first()

        if dup:
            changed = any([
                dup.teacher != item["teacher"],
                dup.location != item["location"],
                dup.end_period != item["end_period"],
                dup.week_start != item["week_start"],
                dup.week_end != item["week_end"],
            ])
            if changed:
                dup.teacher = item["teacher"]
                dup.location = item["location"]
                dup.end_period = item["end_period"]
                dup.week_start = item["week_start"]
                dup.week_end = item["week_end"]
                result.updated += 1
            else:
                result.skipped += 1
            continue

        db.add(Course(
            class_group_id=cg.id,
            semester=semester,
            name=item["title"],
            teacher=item["teacher"],
            location=item["location"],
            day_of_week=item["weekday"],
            start_period=item["start_period"],
            end_period=item["end_period"],
            week_start=item["week_start"],
            week_end=item["week_end"],
            credit=None,
        ))
        result.created += 1

    db.commit()
    return result