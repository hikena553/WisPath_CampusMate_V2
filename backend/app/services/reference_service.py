"""开源参考库服务：检索可合法复用的开源项目，并生成符合本项目规范的页面骨架。

合规立场：本模块不抓取、不搬运任何闭源/受限代码；只登记许可证允许改造复用的
开源项目，并在生成的骨架里强制带上出处署名与许可证提示，替代"逆向搬运他人项目"。
"""
import logging
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.reference import OpenSourceReference
from app.services.knowledge_service import _escape_like, segment_query

logger = logging.getLogger(__name__)

# 许可证合规分级：仅 permissive 可放心商用改造，copyleft 有传染性需谨慎
LICENSE_CATEGORY_LABEL = {
    "permissive": "宽松许可证（可商用/改造，需保留版权与许可声明）",
    "weak-copyleft": "弱传染许可证（库内修改需回馈，链接调用一般无碍）",
    "copyleft": "强传染许可证（衍生作品需同样开源，谨慎引入闭源项目）",
    "unknown": "许可证未知（引入前请人工确认授权）",
}

# 需求关键词 → 页面骨架区块（决定生成模板里出现哪些结构）
_BLOCK_RULES = [
    (("筛选", "搜索", "过滤", "条件", "查询"), "filter-bar"),
    (("统计", "指标", "概览", "总览", "看板", "数据卡"), "stat-cards"),
    (("图表", "趋势", "曲线", "折线", "柱状", "饼图", "分析", "可视化"), "chart"),
    (("列表", "表格", "明细", "记录", "清单"), "table"),
    (("表单", "填写", "申请", "提交", "录入"), "form"),
    (("时间线", "轨迹", "历程", "成长"), "timeline"),
    (("标签", "分类", "tab", "页签"), "tabs"),
    (("作品", "项目", "网格", "卡片墙", "画廊"), "card-grid"),
]

# 需求关键词 → 页面组件名（PascalCase），用于给脚手架起一个贴合业务的名字
_NAME_RULES = [
    (("成绩", "分数", "gpa"), "GradeAnalysis"),
    (("课表", "课程", "排课"), "Schedule"),
    (("请假", "审批"), "Leave"),
    (("通知", "公告"), "Announcement"),
    (("学生", "学员"), "Students"),
    (("作品", "项目经历"), "Portfolio"),
    (("社区", "帖子"), "Community"),
    (("资源", "资料"), "Resources"),
    (("消息", "会话"), "Messages"),
    (("档案", "履历"), "Archive"),
    (("计划", "任务"), "Plan"),
    (("统计", "看板", "仪表"), "Dashboard"),
]


def _to_pascal_case(raw: str) -> str:
    """把任意字符串规整为合法的 PascalCase 组件名。"""
    cleaned = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", raw or "").strip()
    if not cleaned:
        return "NewPage"
    parts = [p for p in cleaned.split() if p]
    if not parts:
        return "NewPage"
    name = "".join(p[0].upper() + p[1:] for p in parts if p)
    name = re.sub(r"[^0-9a-zA-Z]", "", name)
    if not name:
        return "NewPage"
    if name[0].isdigit():
        name = "P" + name
    return name


def _infer_page_name(requirement: str, page_name: str | None) -> str:
    if page_name and page_name.strip():
        return _to_pascal_case(page_name)
    low = requirement.lower()
    for keywords, name in _NAME_RULES:
        if any(kw in low for kw in keywords):
            return name
    return "NewPage"


def _infer_blocks(requirement: str) -> list[str]:
    blocks: list[str] = []
    for keywords, block in _BLOCK_RULES:
        if any(kw in requirement for kw in keywords) and block not in blocks:
            blocks.append(block)
    if not blocks:
        blocks = ["stat-cards", "table"]
    # 保证顺序稳定：按规则表顺序输出
    order = [b for _, b in _BLOCK_RULES]
    return sorted(blocks, key=lambda b: order.index(b))


def _to_kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


# ---------------- 参考库 CRUD ----------------

def list_references(
    db: Session,
    *,
    search: str | None = None,
    license_category: str | None = None,
    enabled_only: bool = False,
    limit: int = 200,
) -> list[OpenSourceReference]:
    query = db.query(OpenSourceReference)
    if enabled_only:
        query = query.filter(OpenSourceReference.enabled.is_(True))
    if license_category:
        query = query.filter(OpenSourceReference.license_category == license_category)
    if search:
        like = f"%{_escape_like(search)}%"
        query = query.filter(
            or_(
                OpenSourceReference.name.like(like, escape="\\"),
                OpenSourceReference.tech_tags.like(like, escape="\\"),
                OpenSourceReference.summary.like(like, escape="\\"),
                OpenSourceReference.reusable_scope.like(like, escape="\\"),
            )
        )
    return query.order_by(OpenSourceReference.stars.desc(), OpenSourceReference.id.asc()).limit(limit).all()


def search_references(
    db: Session,
    query_text: str,
    *,
    limit: int = 5,
    license_category: str | None = None,
) -> list[OpenSourceReference]:
    """按需求关键词检索参考库：命中关键词越多、收藏量越高，排序越靠前。"""
    tokens = segment_query(query_text)
    candidates = list_references(db, license_category=license_category, enabled_only=True, limit=500)
    if not candidates:
        return []

    def score(item: OpenSourceReference) -> tuple[int, int]:
        haystack = " ".join(
            str(x or "")
            for x in (item.name, item.tech_tags, item.summary, item.reusable_scope, item.license)
        ).lower()
        hits = sum(1 for t in tokens if t and t.lower() in haystack)
        return (hits, item.stars)

    scored = [(score(item), item) for item in candidates]
    matched = [(s, item) for s, item in scored if s[0] > 0]
    matched.sort(key=lambda pair: pair[0], reverse=True)
    if not matched:
        # 无命中时回退为「最热门的宽松许可证项目」，保证脚手架有参考来源
        matched = [((0, item.stars), item) for item in candidates[:limit]]
    return [item for _, item in matched[:limit]]


def get_reference(db: Session, ref_id: int) -> OpenSourceReference | None:
    return db.query(OpenSourceReference).filter(OpenSourceReference.id == ref_id).first()


def create_reference(db: Session, **kwargs) -> OpenSourceReference:
    item = OpenSourceReference(**kwargs)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_reference(db: Session, ref_id: int, **kwargs) -> OpenSourceReference | None:
    item = get_reference(db, ref_id)
    if not item:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_reference(db: Session, ref_id: int) -> bool:
    item = get_reference(db, ref_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


# ---------------- 页面脚手架生成 ----------------

def _build_attribution(refs: list[OpenSourceReference]) -> str:
    lines = [
        "/**",
        " * 本页面骨架由「开源参考复用工作流」生成（本地模板生成，非 AI 生成）。",
        " * 参考的开源项目（请保留署名，并遵守各自的许可证）：",
    ]
    if refs:
        for r in refs:
            scope = (r.reusable_scope or "见项目文档").strip()
            lines.append(f" * - {r.name} ({r.license}) {r.repo_url}")
            lines.append(f" *     可复用范围：{scope}")
    else:
        lines.append(" * - （未匹配到参考项目，请在管理端「开源参考库」补充）")
    lines.append(" * 合规提示：仅复用许可证允许的范围；GPL 系（强传染）项目请勿直接拷入闭源项目。")
    lines.append(" */")
    return "\n".join(lines)


def _render_filter_bar() -> str:
    return """      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="keyword"
          placeholder="搜索关键词"
          clearable
          class="filter-input"
          @keyup.enter="loadData"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" :loading="loading" @click="loadData">查询</el-button>
      </div>"""


def _render_stat_cards() -> str:
    return """      <!-- 统计卡片 -->
      <div class="stat-cards">
        <div v-for="s in stats" :key="s.label" class="stat-card">
          <span class="stat-value">{{ s.value }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>"""


def _render_chart() -> str:
    return """      <!-- 图表区 -->
      <div class="card chart-card">
        <div class="card-title">趋势分析</div>
        <div ref="chartRef" class="chart-box"></div>
      </div>"""


def _render_table() -> str:
    return """      <!-- 数据列表 -->
      <div class="card">
        <div class="card-title">数据列表</div>
        <el-table :data="rows" v-loading="loading" stripe>
          <el-table-column prop="name" label="名称" min-width="140" />
          <el-table-column prop="value" label="数值" width="120" />
          <el-table-column prop="updatedAt" label="更新时间" min-width="160" />
        </el-table>
        <el-empty v-if="!loading && rows.length === 0" description="暂无数据" />
      </div>"""


def _render_form() -> str:
    return """      <!-- 填写表单 -->
      <div class="card">
        <div class="card-title">信息填写</div>
        <el-form :model="form" label-width="88px" class="edit-form">
          <el-form-item label="标题">
            <el-input v-model="form.title" placeholder="请输入标题" />
          </el-form-item>
          <el-form-item label="说明">
            <el-input v-model="form.detail" type="textarea" :rows="3" placeholder="请输入说明" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="submit">提交</el-button>
          </el-form-item>
        </el-form>
      </div>"""


def _render_timeline() -> str:
    return """      <!-- 时间线 -->
      <div class="card">
        <div class="card-title">时间线</div>
        <el-timeline>
          <el-timeline-item
            v-for="item in rows"
            :key="item.name"
            :timestamp="item.updatedAt"
            placement="top"
          >
            {{ item.name }}
          </el-timeline-item>
        </el-timeline>
      </div>"""


def _render_tabs() -> str:
    return """      <!-- 分类页签 -->
      <el-tabs v-model="activeTab" class="tabs">
        <el-tab-pane v-for="t in tabs" :key="t" :label="t" :name="t" />
      </el-tabs>"""


def _render_card_grid() -> str:
    return """      <!-- 卡片网格 -->
      <div class="card-grid">
        <div v-for="item in rows" :key="item.name" class="grid-card">
          <div class="grid-title">{{ item.name }}</div>
          <div class="grid-desc">{{ item.value }}</div>
        </div>
      </div>"""


_BLOCK_RENDERERS = {
    "filter-bar": _render_filter_bar,
    "stat-cards": _render_stat_cards,
    "chart": _render_chart,
    "table": _render_table,
    "form": _render_form,
    "timeline": _render_timeline,
    "tabs": _render_tabs,
    "card-grid": _render_card_grid,
}


def generate_scaffold(
    db: Session,
    *,
    requirement: str,
    page_name: str | None = None,
    include_reference_ids: list[int] | None = None,
) -> dict:
    """按需求生成 Vue 页面骨架（本地模板生成）。

    返回结构对应 schemas.reference.ScaffoldResponse。
    """
    name = _infer_page_name(requirement, page_name)
    route_path = f"/{_to_kebab(name)}"
    blocks = _infer_blocks(requirement)

    if include_reference_ids:
        refs = [r for r in (get_reference(db, i) for i in include_reference_ids) if r]
    else:
        refs = search_references(db, requirement, limit=4)

    attribution = _build_attribution(refs)

    body = "\n\n".join(_BLOCK_RENDERERS[b]() for b in blocks)

    template = f"""{attribution}
<template>
  <div class="page">
    <header class="page-header">
      <h2 class="page-title">{name}</h2>
      <span class="page-sub">{{{{ requirement }}}}</span>
    </header>

    <div class="page-body">
{body}
    </div>
  </div>
</template>"""

    script = """<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from 'lucide-vue-next'

// 需求描述（生成时写入，可自行修改）
const requirement = '__REQUIREMENT__'

const loading = ref(false)
const submitting = ref(false)
const keyword = ref('')
const activeTab = ref('全部')
const tabs = ['全部', '待处理', '已完成']

const stats = ref([
  { label: '总数', value: 0 },
  { label: '进行中', value: 0 },
  { label: '已完成', value: 0 },
])
const rows = ref<Array<{ name: string; value: number | string; updatedAt: string }>>([])
const form = ref({ title: '', detail: '' })

const chartRef = ref<HTMLElement | null>(null)
let chart: any = null

async function loadData() {
  loading.value = true
  try {
    // TODO: 替换为真实接口，例如 const data = await fetchXxx({ keyword: keyword.value })
    rows.value = []
  } catch {
    ElMessage.error('加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.value.title) {
    ElMessage.warning('请先填写标题')
    return
  }
  submitting.value = true
  try {
    // TODO: 替换为真实提交接口
    ElMessage.success('已提交')
    form.value = { title: '', detail: '' }
    await loadData()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadData()
})

onUnmounted(() => {
  chart?.dispose?.()
  chart = null
})
</script>""".replace("__REQUIREMENT__", requirement.replace("'", "\\'"))

    style = """<style scoped>
.page {
  padding: 24px 28px;
}
.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
}
.page-sub {
  font-size: 13px;
  color: #94a3b8;
}
.page-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 16px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 12px;
}
.filter-bar {
  display: flex;
  gap: 10px;
}
.filter-input {
  max-width: 280px;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 16px;
}
.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #2563eb;
}
.stat-label {
  font-size: 13px;
  color: #94a3b8;
}
.chart-box {
  width: 100%;
  height: 280px;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}
.grid-card {
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 14px;
}
.grid-title {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}
.grid-desc {
  margin-top: 6px;
  font-size: 13px;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .page { padding: 14px 16px; }
  .filter-bar { flex-direction: column; }
  .filter-input { max-width: none; }
}
</style>"""

    notes = [
        "骨架为本地模板生成，结构与区块按需求关键词推断，请按实际业务替换 TODO 处的接口调用。",
        f"已匹配 {len(refs)} 个参考项目，请在文件头保留署名并核对许可证。",
        "仅复用许可证允许的范围：permissive（MIT/Apache/BSD）可商用改造；GPL 系请勿直接拷入闭源项目。",
    ]

    return {
        "page_name": name,
        "route_path": route_path,
        "matched_references": refs,
        "attribution": attribution,
        "files": {f"{name}.vue": f"{template}\n\n{script}\n\n{style}"},
        "notes": notes,
    }
