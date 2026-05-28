import logging
from typing import List, Optional
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

# Optional import — not available in CI (no torch).
# Tests patch this module-level name before instantiation.
try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


class CrossEncoderReranker(BaseNodePostprocessor):
    """Custom Cross-Encoder Reranker using sentence-transformers ms-marco models."""

    model_name: str
    top_n: int
    _model: object  # CrossEncoder instance

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        top_n: int = 3,
    ):
        super().__init__(model_name=model_name, top_n=top_n)
        # CrossEncoder is the module-level name — patchable in tests even when
        # sentence-transformers is not installed (CI environment).
        encoder_cls = CrossEncoder
        if encoder_cls is None:
            raise ImportError(
                "sentence-transformers is required for CrossEncoderReranker. "
                "Install with: pip install sentence-transformers"
            )
        # Use object.__setattr__ to bypass Pydantic field validation
        object.__setattr__(self, "_model", encoder_cls(model_name))
        logger.info(
            f"CrossEncoderReranker successfully loaded with model: {model_name}"
        )

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Performs batch prediction across query-candidate pairs and ranks them."""
        if not nodes or not query_bundle:
            return nodes

        query = query_bundle.query_str

        # 1. Batch inference setup
        pairs = [[query, n.node.text] for n in nodes]

        try:
            # 2. Predict scores in a single batched run
            scores = self._model.predict(pairs)

            # 3. Update scores on candidate nodes
            for idx, score in enumerate(scores):
                nodes[idx].score = float(score)

            # 4. Sort in descending order
            nodes = sorted(nodes, key=lambda x: x.score, reverse=True)

            logger.info(
                f"Reranking successful. Filtered {len(nodes)} nodes down to top {self.top_n}."
            )
            return nodes[: self.top_n]
        except Exception as e:
            logger.error(f"CrossEncoder reranking failed: {e}")
            return nodes[: self.top_n]
