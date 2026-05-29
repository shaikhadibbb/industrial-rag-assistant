import os
import logging
import yaml

logger = logging.getLogger(__name__)


class BGEEmbedder:
    """Wrapper for BAAI/bge embedding model.

    Uses FastEmbed (ONNX, no PyTorch) when USE_FASTEMBED=true — required for
    Render free tier (512MB RAM). Falls back to HuggingFaceEmbedding locally.
    """

    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.model_name = config["embedding"]["model_name"]
        self.batch_size = config["embedding"]["batch_size"]
        self.use_fastembed = os.getenv("USE_FASTEMBED", "false").lower() == "true"

        if self.use_fastembed:
            self._load_fastembed()
        else:
            self._load_huggingface()

    def _load_fastembed(self) -> None:
        """Load via FastEmbed — ONNX-based, no PyTorch, fits in 512MB RAM."""
        logger.info(f"Loading embedding model via FastEmbed (ONNX): {self.model_name}")
        from llama_index.embeddings.fastembed import FastEmbedEmbedding

        self.embed_model = FastEmbedEmbedding(
            model_name=self.model_name,
            cache_dir="./.cache/fastembed",
        )

    def _load_huggingface(self) -> None:
        """Load via HuggingFace — full PyTorch model, for local dev only."""
        logger.info(f"Loading embedding model via HuggingFace: {self.model_name}")
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        # Monkeypatch Pydantic v2 field defaults to resolve library-level ValidationError
        if hasattr(HuggingFaceEmbedding, "model_fields"):
            HuggingFaceEmbedding.model_fields["cache_folder"].default = None
            HuggingFaceEmbedding.model_fields["query_instruction"].default = None
            HuggingFaceEmbedding.model_fields["text_instruction"].default = None
            HuggingFaceEmbedding.model_rebuild(force=True)  # type: ignore[attr-defined]

        self.embed_model = HuggingFaceEmbedding(
            model_name=self.model_name,
            embed_batch_size=self.batch_size,
            cache_folder="./.cache/huggingface",
        )

    def get_embedding_model(self) -> object:
        """Returns the LlamaIndex compatible embedding model."""
        return self.embed_model
