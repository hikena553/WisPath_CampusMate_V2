"""上游模型输出净化：剥离泄漏进正文的控制标签。

DeepSeek 系模型（经代理调用）在输入不可判定时会把自己的安全审核结论当正文吐出来，形如：

    <ds_safety>[用户未成年]否[分类]其他[判定]…[规则]无
    </ds_safety>Safe

这段文本会顺着流式链路一路往下走：ai_text 进气泡、切句后送 TTS 被**朗读出来**
（实测把"[判定]…属于安全回复"念了 4 句）。上游行为不可控，只能在我们的流式边界上剥离。

流式难点：标签会被 token 切碎（"<ds_saf" + "ety>"），所以不能简单正则替换，
必须用状态机把"可能是半个标签"的尾巴留在缓冲里等下一个 delta。
"""
import re

_OPEN = "<ds_safety>"
_CLOSE = "</ds_safety>"
# 闭合标签之后紧跟的判定结论（Safe / safe），只在紧邻位置剥离一次。
# 不能用 \b：中文紧跟在 "Safe" 后面时（"Safe今天"）两个都是 Unicode 词字符，
# \b 不成立会漏剥；用"后面不是英文字母"判断才稳。
_LEADING_MARK = re.compile(r"^\s*Safe(?![A-Za-z])", re.IGNORECASE)
# 非流式兜底：整段清洗（尾部判定词可选，且不吃掉它后面的换行）
_BLOCK_RE = re.compile(
    r"<ds_safety>.*?</ds_safety>(?:\s*Safe(?![A-Za-z]))?",
    re.IGNORECASE | re.DOTALL,
)


class SafetyTagFilter:
    """流式剥离 <ds_safety>…</ds_safety> 及其后的 Safe 标记。

    用法::

        f = SafetyTagFilter()
        for delta in stream:
            out = f.feed(delta)
            if out:
                emit(out)
        tail = f.flush()
        if tail:
            emit(tail)
    """

    def __init__(self) -> None:
        self._pending = ""      # 可能是半个标签的尾巴，等下一个 delta
        self._inside = False    # 正在标签体内，内容全部丢弃
        self._after_close = False  # 刚闭合，下一个文本块开头的 "Safe" 要吃掉

    @staticmethod
    def _partial_tail(buf: str, start: int, tag: str) -> int:
        """buf[start:] 末尾有多少字符可能是 tag 的前缀（用于留待下次拼接）。"""
        tail = buf[start:]
        for k in range(min(len(tag) - 1, len(tail)), 0, -1):
            if tag.startswith(tail[-k:]):
                return k
        return 0

    def feed(self, text: str) -> str:
        buf = self._pending + (text or "")
        self._pending = ""
        if not buf:
            return ""

        out: list[str] = []
        i = 0
        n = len(buf)

        while i < n:
            if self._inside:
                j = buf.find(_CLOSE, i)
                if j < 0:
                    # 闭合标签可能还没到齐：把疑似半个 "</ds_safety>" 留到下次
                    keep = self._partial_tail(buf, i, _CLOSE)
                    self._pending = buf[n - keep:] if keep else ""
                    return "".join(out)
                i = j + len(_CLOSE)
                self._inside = False
                self._after_close = True
                continue

            open_j = buf.find(_OPEN, i)
            close_j = buf.find(_CLOSE, i)
            if close_j >= 0 and (open_j < 0 or close_j < open_j):
                # 孤立的闭合标签（开标签被上游吞掉）：整段丢弃
                visible = self._consume_mark(buf[i:close_j])
                if visible:
                    out.append(visible)
                i = close_j + len(_CLOSE)
                self._after_close = True
                continue
            if open_j < 0:
                # 末尾可能是半个开标签或半个闭合标签，都要扣住等下次
                keep = max(self._partial_tail(buf, i, _OPEN),
                           self._partial_tail(buf, i, _CLOSE))
                visible = buf[i:n - keep] if keep else buf[i:]
                self._pending = buf[n - keep:] if keep else ""
                visible = self._consume_mark(visible)
                if visible:
                    out.append(visible)
                return "".join(out)

            visible = self._consume_mark(buf[i:open_j])
            if visible:
                out.append(visible)
            i = open_j + len(_OPEN)
            self._inside = True

        return "".join(out)

    def _consume_mark(self, text: str) -> str:
        """标签闭合后紧跟的 Safe 判定结论不属于回复内容。

        "Safe" 自己也可能被 token 切开（"Saf" + "e"），遇到它的前缀时先扣住，
        等下一个 delta 到齐再判断，避免半个判定词漏进气泡。
        """
        if not self._after_close or not text:
            return text
        stripped = text.lstrip()
        if not stripped:
            self._pending = text
            return ""
        if len(stripped) < 4 and "safe".startswith(stripped.lower()):
            self._pending = text
            return ""
        self._after_close = False
        return _LEADING_MARK.sub("", text, count=1)

    def flush(self) -> str:
        """流结束时吐出残留（未闭合的标签体一律丢弃）。"""
        rest, self._pending = self._pending, ""
        if self._inside:
            self._inside = False
            self._after_close = False
            return ""
        if self._after_close:
            self._after_close = False
            stripped = rest.lstrip()
            if not stripped:
                return ""
            if len(stripped) < 4 and "safe".startswith(stripped.lower()):
                # 流结束在半个 "Safe" 上：它是判定词残片，丢弃
                return ""
            return _LEADING_MARK.sub("", rest, count=1)
        return rest


def strip_control_tags(text: str) -> str:
    """非流式整段清洗：用于非流式接口、入库前兜底、历史修复。"""
    if not text:
        return text
    cleaned = _BLOCK_RE.sub("", text)
    # 只有闭合/开标签没有配对的残片，一并清掉，避免半个标签露出来
    cleaned = cleaned.replace(_OPEN, "").replace(_CLOSE, "")
    cleaned = _SCAFFOLD_BLOCK_RE.sub("", cleaned)
    cleaned = _SCAFFOLD_BARE_RE.sub("", cleaned)
    return cleaned.strip()


# ===== 脚手架标签：推理/答案结构标记泄漏进正文 =====
# 上游代理偶发把模型内部的结构标签当正文吐出（实测问候轮次输出
# "<answer>好，我记住了…"）。这些标签会进气泡、被 _is_speakable 判定为
# 可朗读后由 TTS 念出 "answer"，必须在流式边界剥离：
#   <think>…</think>   推理块：整体丢弃（推理过程不该给用户，更不能被朗读）
#   <answer> </answer>  答案结构标签：只剥标签、保留正文
_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"
_SCAFFOLD_STRIP_TAGS = ("<answer>", "</answer>")
_SCAFFOLD_TAGS = (_THINK_OPEN, _THINK_CLOSE) + _SCAFFOLD_STRIP_TAGS
# 非流式兜底：整段清洗
_SCAFFOLD_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_SCAFFOLD_BARE_RE = re.compile(r"</?(?:think|answer)>", re.IGNORECASE)


class ScaffoldTagFilter:
    """流式剥离泄漏的脚手架标签（<think> 块整体丢弃，<answer> 只剥标签）。

    与 SafetyTagFilter 同一套状态机思路：标签可能被 token 切碎
    （"<answ" + "er>"），末尾可能是半个标签前缀的部分必须扣住等下一个 delta。
    """

    def __init__(self) -> None:
        self._pending = ""        # 可能是半个标签的尾巴，等下一个 delta
        self._inside_think = False  # 正在推理块内，内容整体丢弃

    @staticmethod
    def _partial_tail_len(buf: str) -> int:
        """buf 末尾有多少字符可能是任一脚手架标签的前缀。"""
        max_len = max(len(t) for t in _SCAFFOLD_TAGS)
        for k in range(min(max_len - 1, len(buf)), 0, -1):
            if any(t.startswith(buf[-k:]) for t in _SCAFFOLD_TAGS):
                return k
        return 0

    def feed(self, text: str) -> str:
        buf = self._pending + (text or "")
        self._pending = ""
        if not buf:
            return ""

        out: list[str] = []
        i = 0
        n = len(buf)
        while i < n:
            if self._inside_think:
                j = buf.find(_THINK_CLOSE, i)
                if j < 0:
                    # 闭合标签可能没到齐：扣住疑似半个 "</think>" 的尾巴
                    keep = self._partial_tail_len(buf[i:])
                    self._pending = buf[n - keep:] if keep else ""
                    return "".join(out)
                i = j + len(_THINK_CLOSE)
                self._inside_think = False
                continue

            hits = [(j, t) for t in _SCAFFOLD_TAGS if (j := buf.find(t, i)) >= 0]
            if not hits:
                keep = self._partial_tail_len(buf[i:])
                visible = buf[i:n - keep] if keep else buf[i:]
                self._pending = buf[n - keep:] if keep else ""
                if visible:
                    out.append(visible)
                return "".join(out)

            j, tag = min(hits, key=lambda x: x[0])
            if j > i:
                out.append(buf[i:j])
            i = j + len(tag)
            if tag == _THINK_OPEN:
                self._inside_think = True
            # <answer>/</answer>：只剥标签本身，正文保留
        return "".join(out)

    def flush(self) -> str:
        """流结束时吐出残留；未闭合的推理块按推理内容丢弃。"""
        rest, self._pending = self._pending, ""
        if self._inside_think:
            self._inside_think = False
            return ""
        return rest


class StreamSanitizer(SafetyTagFilter):
    """SafetyTagFilter + ScaffoldTagFilter 串联。

    一条流式边界同时剥离安全审核标注与脚手架标签。feed/flush 接口与
    SafetyTagFilter 完全一致，可直接原地替换。
    """

    def __init__(self) -> None:
        super().__init__()
        self._scaffold = ScaffoldTagFilter()

    def feed(self, text: str) -> str:
        return self._scaffold.feed(super().feed(text))

    def flush(self) -> str:
        # super().flush() 吐出的扣留尾巴是"新文本"，须先过 scaffold.feed
        # 处理其中可能被切碎的标签，再取 scaffold 自身的残留
        tail = self._scaffold.feed(super().flush())
        return tail + self._scaffold.flush()
