import pytest
from unittest.mock import MagicMock, PropertyMock, patch

from app.services.knowledge_service import search_knowledge, _split_text


class TestKnowledgeSearch:
    def test_empty_query_returns_empty(self):
        db = MagicMock(name="db")
        db.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        result = search_knowledge(db, "", limit=5)
        assert result == []

    def test_returns_qa_results_when_keywords_match(self):
        db = MagicMock(name="db")
        mock_item = MagicMock(name="KnowledgeItem")
        type(mock_item).category = PropertyMock(return_value="办事流程")
        type(mock_item).question = PropertyMock(return_value="怎么请假")
        type(mock_item).answer = PropertyMock(return_value="请假流程说明")
        type(mock_item).tags = PropertyMock(return_value="请假,流程")

        # 模拟KnowledgeItem查询以返回结果
        qa_filter = MagicMock(name="qa_filter")
        qa_filter.limit.return_value.all.return_value = [mock_item]
        qa_query = MagicMock(name="qa_query")
        qa_query.filter.return_value = qa_filter

        # 模拟DocumentChunk查询以返回空结果
        doc_filter = MagicMock(name="doc_filter")
        doc_filter.limit.return_value.all.return_value = []
        doc_query = MagicMock(name="doc_query")
        doc_query.filter.return_value = doc_filter

        from app.models.knowledge import KnowledgeItem
        from app.models.document import DocumentChunk

        def query_side_effect(model_cls):
            if model_cls is KnowledgeItem:
                return qa_query
            if model_cls is DocumentChunk:
                return doc_query
            return MagicMock()
        db.query.side_effect = query_side_effect

        result = search_knowledge(db, "请假", limit=5)
        assert len(result) == 1
        assert result[0]["type"] == "qa"
        assert result[0]["category"] == "办事流程"

    def test_returns_document_when_qa_insufficient(self):
        db = MagicMock(name="db")
        mock_item = MagicMock(name="KnowledgeItem")
        type(mock_item).category = PropertyMock(return_value="办事流程")
        type(mock_item).question = PropertyMock(return_value="怎么请假")
        type(mock_item).answer = PropertyMock(return_value="请假流程说明")
        type(mock_item).tags = PropertyMock(return_value="请假,流程")

        mock_chunk = MagicMock(name="DocumentChunk")
        type(mock_chunk).content = PropertyMock(return_value="文档内容片段")
        type(mock_chunk).document_id = PropertyMock(return_value=1)

        qa_filter = MagicMock(name="qa_filter")
        qa_filter.limit.return_value.all.return_value = [mock_item]
        qa_query = MagicMock(name="qa_query")
        qa_query.filter.return_value = qa_filter

        doc_filter = MagicMock(name="doc_filter")
        doc_filter.limit.return_value.all.return_value = [mock_chunk]
        doc_query = MagicMock(name="doc_query")
        doc_query.filter.return_value = doc_filter

        from app.models.knowledge import KnowledgeItem
        from app.models.document import DocumentChunk

        def query_side_effect(model_cls):
            if model_cls is KnowledgeItem:
                return qa_query
            if model_cls is DocumentChunk:
                return doc_query
            return MagicMock()
        db.query.side_effect = query_side_effect

        result = search_knowledge(db, "请假", limit=5)
        assert len(result) == 2
        assert result[0]["type"] == "qa"
        assert result[1]["type"] == "document"


class TestSplitText:
    def test_empty_text(self):
        assert _split_text("") == []

    def test_simple_split(self):
        text = "a" * 600
        chunks = _split_text(text, chunk_size=200, overlap=20)
        assert len(chunks) == 4
        assert all(len(c) <= 200 for c in chunks)

    def test_overlap_preserved(self):
        text = "HelloWorld"
        chunks = _split_text(text, chunk_size=5, overlap=2)
        assert len(chunks) >= 2
