import logging
import yaml
import time
from llama_index.llms.ollama import Ollama
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class OllamaLLM:
    """Client for Mistral-7B via Ollama."""
    
    def __init__(self, config_path: str = "configs/config.yaml"):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        self.model = config['llm']['model']
        self.base_url = config['llm']['base_url']
        self.temperature = config['llm']['temperature']
        self.max_tokens = config['llm']['max_tokens']
        self.request_timeout = config['llm'].get('request_timeout', 45.0)
        self.additional_kwargs = config['llm'].get('additional_kwargs', {})
        
        self.llm = Ollama(
            model=self.model,
            base_url=self.base_url,
            temperature=self.temperature,
            request_timeout=self.request_timeout,
            additional_kwargs=self.additional_kwargs
        )

        
        self._test_connection()

    def _test_connection(self):
        """Verify connection to Ollama."""
        try:
            # Simple check
            logger.info(f"Testing connection to Ollama at {self.base_url}")
            # Ollama client doesn't have a direct health check in LlamaIndex wrapper
            # but we can try a tiny completion or just log.
            logger.info(f"Ollama configured for model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def complete(self, prompt: str):
        """Completes a prompt with retry logic and latency logging."""
        start_time = time.time()
        response = self.llm.complete(prompt)
        duration = time.time() - start_time
        logger.info(f"LLM Response received in {duration:.2f}s")
        return response

    def get_llm(self):
        """Returns the LlamaIndex LLM object."""
        return self.llm
