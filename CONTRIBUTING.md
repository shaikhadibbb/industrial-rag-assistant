# Contributing to Industrial RAG Assistant

Thank you for contributing! We follow strict engineering standards to build a secure, high-quality, and robust product.

---

## 💻 Local Development Setup

### Prerequisites
- Python 3.11
- Docker (for Qdrant)
- Ollama (installed locally)

### Step-by-Step Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/shaikhadibbb/industrial-rag-assistant.git
   cd industrial-rag-assistant
   ```

2. **Initialize and activate virtual environment:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

3. **Install exact dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Run Services:**
   - **Qdrant (via Docker):**
     ```bash
     docker-compose up -d qdrant
     ```
   - **Ollama (local):**
     Ensure Ollama is running and download the instruct model:
     ```bash
     ollama pull mistral:7b-instruct
     ```

5. **Start System:**
   ```bash
   ./launch.sh
   ```

---

## 🧪 Testing Guidelines

We write tests for *every* new feature. All tests must be fast, reliable, and pass locally before making a Pull Request.

### Running the Test Suite
- Run all tests (unit tests and online integration tests if services are up):
  ```bash
  pytest -v
  ```
- Run unit tests only:
  ```bash
  pytest tests/unit/ -v
  ```

### Code Formatting & Quality
Before committing, format and lint the code using the configured tools:
- **Lint Check:**
  ```bash
  ruff check src/ tests/
  ```
- **Code Formatter:**
  ```bash
  black --check src/ tests/
  ```

---

## 📝 Commit Conventions

We strictly enforce **Conventional Commits** for all git history. Commits must follow this format:

```text
<type>(<scope>): <description>
```

### Core Types:
- `feat:` A new feature or endpoint.
- `fix:` A bug fix or security patch.
- `docs:` Documentation-only changes (e.g., README or architecture updates).
- `test:` Adding or updating tests.
- `chore:` Maintenance tasks, dependency bumps, or tool configurations.

### Examples:
- `feat: integrate reciprocal rank fusion for hybrid retrieval`
- `fix: sanitize pdf filename to prevent path traversals`
- `docs: add detailed RAGAS metrics explanation`
