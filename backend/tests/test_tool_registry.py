import pytest
from app.services.tool_registry import TOOL_DEFINITIONS, TEACHER_TOOL_DEFINITIONS


class TestToolDefinitions:
    def test_has_expected_student_tool_names(self):
        names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
        assert "create_leave" in names
        assert "create_growth_record" in names
        assert "update_project_stage" in names
        assert "submit_service_request" in names
        assert "query_schedule" in names
        assert "query_grades" in names
        assert "query_exams" in names
        assert "query_knowledge" in names
        assert "query_sceneries" in names
        assert "query_announcements" in names

    def test_student_tools_have_correct_count(self):
        assert len(TOOL_DEFINITIONS) == 13

    def test_each_tool_has_required_keys(self):
        for tool in TOOL_DEFINITIONS:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

    def test_tools_have_valid_json_schema(self):
        for tool in TOOL_DEFINITIONS:
            params = tool["function"]["parameters"]
            assert params["type"] == "object"
            assert "properties" in params


class TestTeacherToolDefinitions:
    def test_has_expected_teacher_tool_names(self):
        names = [t["function"]["name"] for t in TEACHER_TOOL_DEFINITIONS]
        assert "query_pending_leaves" in names
        assert "query_students" in names
        assert "query_crisis_alerts" in names
        assert "approve_leave" in names
        assert "query_student_detail" in names
        assert "query_growth_stats" in names
        assert "query_knowledge" in names
        assert "query_announcements" in names

    def test_teacher_tools_have_correct_count(self):
        assert len(TEACHER_TOOL_DEFINITIONS) == 9

    def test_each_teacher_tool_has_required_keys(self):
        for tool in TEACHER_TOOL_DEFINITIONS:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            fn = tool["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn

    def test_student_knowledge_tool_matches_teacher_version(self):
        student_knowledge = next(
            t["function"]["name"] for t in TOOL_DEFINITIONS if t["function"]["name"] == "query_knowledge"
        )
        teacher_knowledge = next(
            t["function"]["name"] for t in TEACHER_TOOL_DEFINITIONS if t["function"]["name"] == "query_knowledge"
        )
        assert student_knowledge == teacher_knowledge
