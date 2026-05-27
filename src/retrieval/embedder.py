import logging
import yaml
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BGEEmbedder:
    """Wrapper for BAAI/bge-m3 embedding model."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        self.model_name = config['embedding']['model_name']
        self.batch_size = config['embedding']['batch_size']
        
        logger.info(f"Loading embedding model: {self.model_name}")
        self.embed_model = HuggingFaceEmbedding(
            model_name=self.model_name,
            embed_batch_size=self.batch_size,
            cache_folder="./.cache/huggingface"
        )

    def get_embedding_model(self):
        """Returns the LlamaIndex compatible embedding model."""
        return self.embed_model
