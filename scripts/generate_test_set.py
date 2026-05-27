import json
import yaml
import logging
from src.retrieval.vector_store import QdrantStore
from src.generation.llm_client import OllamaLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_set(config_path: str = "configs/config.yaml"):
    """Generates synthetic Q&A pairs from chunks in Qdrant."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    store = QdrantStore()
    llm = OllamaLLM()
    
    # 1. Fetch some chunks (using Qdrant client directly)
    collection_name = config['vector_store']['collection_name']
    points = store.client.scroll(collection_name=collection_name, limit=5)[0]
    
    test_set = []
    
    for point in points:
        chunk_text = point.payload['text']
        
        prompt = f"""
        Given the following industrial document chunk, generate 3 high-quality Q&A pairs.
        Each pair should consist of a 'question' (factual or procedural) and a 'ground_truth' answer derived directly from the text.
        
        Chunk:
        {chunk_text}
        
        Output format: JSON list of objects with 'question' and 'ground_truth'.
        """
        
        try:
            response = llm.complete(prompt)
            # Basic parsing - LLM might return raw text with JSON
            # In production, we'd use structured output, here we do a simple extract
            text_resp = response.text
            start = text_resp.find("[")
            end = text_resp.rfind("]") + 1
            qa_pairs = json.loads(text_resp[start:end])
            
            for qa in qa_pairs:
                qa['ground_truth'] = qa['ground_truth'] # already there
                test_set.append({
                    "question": qa['question'],
                    "ground_truth": qa['ground_truth'],
                    "context": chunk_text
                })
        except Exception as e:
            logger.error(f"Failed to generate QA for chunk: {e}")
            
    with open("data/test_set.json", "w") as f:
        json.dump(test_set, f, indent=4)
        
    logger.info(f"Generated {len(test_set)} test pairs in data/test_set.json")

if __name__ == "__main__":
    generate_test_set()
