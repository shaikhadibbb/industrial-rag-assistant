import pytest
from llama_index.core.schema import NodeWithScore, TextNode
from src.retrieval.query_engine import DeduplicationPostprocessor

def test_deduplication_postprocessor():
    postprocessor = DeduplicationPostprocessor(similarity_threshold=0.85)
    
    # Prepare nodes with identical text but different pages
    node1 = NodeWithScore(node=TextNode(text="This is a unique chunk of text that has long details about machinery.", metadata={"page_label": "1"}), score=0.9)
    node2 = NodeWithScore(node=TextNode(text="This is a unique chunk of text that has long details about machinery.", metadata={"page_label": "2"}), score=0.8)
    node3 = NodeWithScore(node=TextNode(text="Completely different context and text that is completely unique.", metadata={"page_label": "3"}), score=0.7)
    
    processed = postprocessor.postprocess_nodes([node1, node2, node3])
    
    assert len(processed) == 2
    assert processed[0] == node1
    assert processed[1] == node3
