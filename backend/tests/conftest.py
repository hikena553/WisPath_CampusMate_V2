import os
import pytest
from unittest.mock import MagicMock, patch

from app.models.user import UserRole

os.environ.setdefault("TESTING", "1")


@pytest.fixture(autouse=True)
def mock_db_settings():
    """阻止LLM配置中的真实数据库调用（由_get_db_settings的try/except优雅处理）"""
    with patch('app.services.llm_service._get_db_settings', return_value={}):
        yield


@pytest.fixture(autouse=True)
def mock_openai_client():
    """模拟OpenAI客户端以阻止真实API调用"""
    with patch('app.services.llm_service._get_client') as mock_get_client:
        client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "测试回复"
        mock_message.tool_calls = None
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = client
        yield client


@pytest.fixture
def mock_user():
    """创建模拟学生用户"""
    user = MagicMock()
    user.id = 1
    user.username = "test_student"
    user.name = "测试学生"
    user.role = UserRole.STUDENT
    user.college = "计算机学院"
    user.avatar = None
    user.skills_json = {"skills": [], "interests": []}
    return user


@pytest.fixture
def mock_teacher():
    """创建模拟教师用户"""
    user = MagicMock()
    user.id = 10
    user.username = "test_teacher"
    user.name = "测试教师"
    user.role = UserRole.TEACHER
    user.college = "计算机学院"
    user.avatar = None
    user.skills_json = None
    return user


@pytest.fixture
def mock_profile():
    """创建模拟学生档案快照"""
    profile = MagicMock()
    profile.academic_score = 50.0
    profile.psychological_risk = 30.0
    profile.engagement_score = 50.0
    profile.growth_score = 50.0
    profile.overall_risk = 20.0
    return profile
