import pytest
from unittest.mock import MagicMock, patch

from app.services.llm_service import build_system_prompt, _get_llm_config
from app.models.user import UserRole


class TestBuildSystemPrompt:
    def test_student_prompt_has_student_role(self, mock_user):
        prompt = build_system_prompt(mock_user)
        assert "同学" in prompt
        assert "绵阳城市学院" in prompt
        assert "智能管家" in prompt

    def test_teacher_prompt_has_teacher_role(self, mock_teacher):
        prompt = build_system_prompt(mock_teacher)
        assert "老师" in prompt
        assert "教学管理助手" in prompt

    def test_student_and_teacher_prompts_differ(self, mock_user, mock_teacher):
        student_prompt = build_system_prompt(mock_user)
        teacher_prompt = build_system_prompt(mock_teacher)
        assert student_prompt != teacher_prompt
        assert "create_leave" in student_prompt
        assert "create_leave" not in teacher_prompt
        assert "approve_leave" not in student_prompt
        assert "approve_leave" in teacher_prompt

    def test_includes_college_when_provided(self, mock_user):
        mock_user.college = "计算机学院"
        prompt = build_system_prompt(mock_user)
        assert "来自计算机学院" in prompt

    def test_no_college_reference_when_none(self):
        user = MagicMock()
        user.role = UserRole.STUDENT
        user.college = None
        prompt = build_system_prompt(user)
        assert "来自" not in prompt

    def test_no_user_provided(self):
        prompt = build_system_prompt(None)
        assert "同学" in prompt
        assert "来自" not in prompt


class TestGetLlmConfig:
    @patch('app.services.llm_service._get_db_settings', return_value={})
    def test_returns_expected_keys(self, mock_db_settings):
        config = _get_llm_config()
        assert "api_key" in config
        assert "base_url" in config
        assert "model" in config
        assert "agent_model" in config
        assert "temperature" in config
        assert "max_tokens" in config

    @patch('app.services.llm_service._get_db_settings', return_value={
        'llm_api_key': 'test-key',
        'llm_base_url': 'https://test.url',
        'llm_model': 'test-model',
        'llm_agent_model': 'test-agent',
        'llm_agent_temperature': '0.5',
        'llm_agent_max_tokens': '5000',
    })
    def test_uses_db_settings_when_available(self, mock_db_settings):
        config = _get_llm_config()
        assert config['api_key'] == 'test-key'
        assert config['base_url'] == 'https://test.url'
        assert config['model'] == 'test-model'
        assert config['agent_model'] == 'test-agent'
        assert config['temperature'] == 0.5
        assert config['max_tokens'] == 5000

    def test_role_based_prompt_differences(self, mock_user, mock_teacher):
        student_prompt = build_system_prompt(mock_user)
        teacher_prompt = build_system_prompt(mock_teacher)
        assert student_prompt != teacher_prompt
