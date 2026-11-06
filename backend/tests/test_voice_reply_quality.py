"""语音回答质量防线测试（语音通话乱码/无声修复）。

上游代理偶发把结构标签当正文吐出（<answer>…、<think>…</think>），或整段退化
（纯竖线串、'\n-1' 残片）。退化内容过不了 _is_speakable，一句语音都合成不出来
（"接通后没声音"），落库后还会以乱码留在聊天页。这里覆盖各道防线：

- llm_guard.ScaffoldTagFilter / StreamSanitizer：流式剥离脚手架标签
- llm_guard.strip_control_tags：非流式整段清洗
- voice_service._is_natural_reply / _greeting_history_slice / _is_stt_language_hallucination
"""
import pytest

from app.utils.llm_guard import ScaffoldTagFilter, StreamSanitizer, strip_control_tags
from app.services.voice_service import (
    _greeting_history_slice,
    _is_natural_reply,
    _is_stt_language_hallucination,
)


def _feed_in_chunks(f, text: str, size: int):
    """按定长分片喂流式过滤器，模拟 token 切碎标签的场景。"""
    return "".join(f.feed(text[i:i + size]) for i in range(0, len(text), size)) + f.flush()


class TestScaffoldTagFilter:
    @pytest.mark.parametrize("size", [1, 2, 3, 5, 7, 64])  # 含把标签切碎的分片
    def test_answer_tag_stripped_keep_body(self, size):
        f = ScaffoldTagFilter()
        out = _feed_in_chunks(f, "<answer>好，我记住了。</answer>还聊吗？", size)
        assert out == "好，我记住了。还聊吗？"

    @pytest.mark.parametrize("size", [1, 3, 4, 8, 64])
    def test_think_block_dropped_entirely(self, size):
        f = ScaffoldTagFilter()
        out = _feed_in_chunks(f, "<think>先想一想他说的宠物</think>你好呀", size)
        assert out == "你好呀"

    def test_unclosed_think_dropped_on_flush(self):
        f = ScaffoldTagFilter()
        out = f.feed("这是推理") + f.feed("还没闭合<think>思考中")
        out += f.flush()
        # <think> 之后的推理内容不给用户
        assert "思考中" not in out

    def test_plain_text_passthrough(self):
        f = ScaffoldTagFilter()
        text = "今天食堂的红烧肉不错，要不要去试试？"
        assert _feed_in_chunks(f, text, 6) == text

    def test_multiple_tags_across_deltas(self):
        f = ScaffoldTagFilter()
        out = _feed_in_chunks(f, "<answer>第一句。</answer>\n<think>internal</think>\n第二句。", 3)
        # 标签整体剥离，正文与正文间的换行保留
        assert out == "第一句。\n\n第二句。"


class TestStreamSanitizer:
    def test_combines_ds_safety_and_scaffold(self):
        f = StreamSanitizer()
        stream = (
            "<ds_safety>[判定]安全</ds_safety>Safe<answer>你好呀"
            "</answer>"
        )
        out = _feed_in_chunks(f, stream, 5)
        assert out == "你好呀"

    def test_interface_matches_safety_filter(self):
        # 语音/文本聊天链路是原地替换，feed/flush 必须同名同参
        f = StreamSanitizer()
        assert f.feed("<answer>好</answer>") == "好"
        assert f.flush() == ""


class TestStripControlTags:
    def test_think_block_removed(self):
        assert strip_control_tags("<think>推理</think>正文") == "正文"

    def test_bare_answer_tags_removed(self):
        assert strip_control_tags("<answer>你好</answer>") == "你好"

    def test_ds_safety_still_removed(self):
        text = "<ds_safety>abc</ds_safety>Safe回复"
        assert strip_control_tags(text) == "回复"


class TestIsNaturalReply:
    def test_pipe_garbage_rejected(self):
        # 实测落库的退化消息：1535 个竖线与空格
        garbage = "<  |  |  |  |  " * 40
        assert not _is_natural_reply(garbage)

    def test_fragment_rejected(self):
        assert not _is_natural_reply("\n")
        assert not _is_natural_reply("\n-1")
        assert not _is_natural_reply("")

    def test_normal_replies_pass(self):
        assert _is_natural_reply("好的。")
        assert _is_natural_reply("你好呀，我在呢～有什么想聊的直接说就行。")
        assert _is_natural_reply("ok, I'll check it.")

    def test_greeting_threshold_stricter(self):
        # 问候重试判定阈值更高：'-1' 这类残片不许当问候语
        assert not _is_natural_reply("-1", min_chars=4)
        assert _is_natural_reply("你好呀我在", min_chars=4)


class TestGreetingHistorySlice:
    def test_trailing_assistant_trimmed(self):
        history = [
            {"role": "user", "content": "我宁愿没刚才的宠物。"},
            {"role": "assistant", "content": "听起来让你有点失落"},
            {"role": "user", "content": "小晨晨，你好呀。"},
            {"role": "assistant", "content": "谢谢愿意跟我说"},
        ]
        out = _greeting_history_slice(history)
        assert [m["role"] for m in out] == ["user", "assistant", "user"]

    def test_trailing_assistants_all_trimmed(self):
        history = [
            {"role": "user", "content": "在吗"},
            {"role": "assistant", "content": "在"},
            {"role": "assistant", "content": "我在"},
        ]
        assert [m["role"] for m in _greeting_history_slice(history)] == ["user"]

    def test_empty_history(self):
        assert _greeting_history_slice([]) == []

    def test_only_assistant_history(self):
        history = [{"role": "assistant", "content": "greeting"}]
        assert _greeting_history_slice(history) == []

    def test_window_size(self):
        history = [{"role": "user", "content": f"m{i}"} for i in range(10)]
        assert len(_greeting_history_slice(history, keep=4)) == 4


class TestSttLanguageHallucination:
    def test_korean_without_han_detected(self):
        # 实测落库的幻觉消息：中文语音被识别成整句韩文
        assert _is_stt_language_hallucination("\ud1b5\ud588\uc73c\uba74 \uc774\uac70.")

    def test_chinese_not_flagged(self):
        assert not _is_stt_language_hallucination("今天天气怎么样？")

    def test_mixed_korean_with_han_not_flagged(self):
        # 同时含汉字与谚文：不确定，宁可放行
        assert not _is_stt_language_hallucination("你好안녕")

    def test_english_not_flagged(self):
        assert not _is_stt_language_hallucination("hello world")

    def test_empty_not_flagged(self):
        assert not _is_stt_language_hallucination("")
