from hypothesis import given, strategies as st
from src.retrieval.query_engine import DeduplicationPostprocessor
from llama_index.core.schema import NodeWithScore, TextNode


@given(st.lists(st.text(min_size=1, max_size=200), min_size=0, max_size=50))
def test_deduplication_never_increases_count(texts: list[str]) -> None:
    processor = DeduplicationPostprocessor(similarity_threshold=0.85)
    nodes = [NodeWithScore(node=TextNode(text=t)) for t in texts]
    result = processor.postprocess_nodes(nodes)
    assert len(result) <= len(nodes)


@given(st.lists(st.text(min_size=1, max_size=200), min_size=0, max_size=50))
def test_deduplication_exact_duplicates_are_removed(texts: list[str]) -> None:
    # Double the list to introduce exact duplicates
    duplicated_texts = texts + texts
    processor = DeduplicationPostprocessor(similarity_threshold=0.85)
    nodes = [NodeWithScore(node=TextNode(text=t)) for t in duplicated_texts]
    result = processor.postprocess_nodes(nodes)
    # The number of unique texts should match or exceed the length of the result
    unique_texts = set(" ".join(t.strip().lower().split()) for t in texts)
    assert len(result) <= len(unique_texts)
