import pytest
from unittest.mock import MagicMock, patch

from app.services.agent_service import select_conversation_strategy, _extract_suggestions


class TestSelectConversationStrategy:
    def test_returns_at_risk_for_high_psychological_risk(self, mock_profile):
        mock_profile.psychological_risk = 70
        mock_profile.overall_risk = 30
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "at_risk"
        assert strategy["style"] == "gentle_care"

    def test_returns_at_risk_for_high_overall_risk(self, mock_profile):
        mock_profile.psychological_risk = 50
        mock_profile.overall_risk = 60
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "at_risk"
        assert strategy["style"] == "gentle_care"

    def test_returns_normal_when_profile_is_none(self):
        name, strategy = select_conversation_strategy(None)
        assert name == "normal"
        assert strategy["style"] == "standard"

    def test_returns_high_performer_for_high_scores(self, mock_profile):
        mock_profile.academic_score = 80
        mock_profile.engagement_score = 70
        mock_profile.psychological_risk = 20
        mock_profile.overall_risk = 10
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "high_performer"
        assert strategy["style"] == "challenge_growth"

    def test_returns_disengaged_for_low_engagement(self, mock_profile):
        mock_profile.academic_score = 50
        mock_profile.engagement_score = 20
        mock_profile.psychological_risk = 20
        mock_profile.overall_risk = 10
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "disengaged"
        assert strategy["style"] == "re_engage"

    def test_returns_normal_fallback(self, mock_profile):
        mock_profile.academic_score = 50
        mock_profile.engagement_score = 50
        mock_profile.psychological_risk = 20
        mock_profile.overall_risk = 10
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "normal"
        assert strategy["style"] == "standard"

    def test_high_risk_overrides_high_performer(self, mock_profile):
        mock_profile.psychological_risk = 65
        mock_profile.academic_score = 90
        mock_profile.engagement_score = 80
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "at_risk"

    def test_high_risk_overrides_disengaged(self, mock_profile):
        mock_profile.overall_risk = 55
        mock_profile.engagement_score = 20
        name, strategy = select_conversation_strategy(mock_profile)
        assert name == "at_risk"

    def test_high_performer_checks_both_scores(self, mock_profile):
        mock_profile.academic_score = 80
        mock_profile.engagement_score = 50
        mock_profile.psychological_risk = 20
        mock_profile.overall_risk = 10
        name, strategy = select_conversation_strategy(mock_profile)
        assert name != "high_performer"


class TestExtractSuggestions:
    def test_extracts_link_style_suggestions(self):
        text = "你可以查看[这篇文章](https://example.com)或[这个教程](https://tutorial.com)"
        result = _extract_suggestions(text)
        assert len(result) == 2
        assert result[0] == {"text": "这篇文章", "link": "https://example.com"}
        assert result[1] == {"text": "这个教程", "link": "https://tutorial.com"}

    def test_returns_empty_list_for_plain_text(self):
        result = _extract_suggestions("这是一段普通的文本，没有任何链接。")
        assert result == []

    def test_returns_empty_for_empty_string(self):
        result = _extract_suggestions("")
        assert result == []

    def test_handles_multiple_links_in_same_text(self):
        text = "推荐[资源A](url1)和[资源B](url2)以及[资源C](url3)"
        result = _extract_suggestions(text)
        assert len(result) == 3
        assert result[0] == {"text": "资源A", "link": "url1"}
        assert result[1] == {"text": "资源B", "link": "url2"}
        assert result[2] == {"text": "资源C", "link": "url3"}

    def test_ignores_bare_urls_without_markdown_syntax(self):
        text = "访问 https://example.com 查看详情"
        result = _extract_suggestions(text)
        assert result == []
