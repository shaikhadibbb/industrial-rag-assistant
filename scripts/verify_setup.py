import os
import sys
import httpx
from qdrant_client import QdrantClient
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify():
    print("\n" + "="*50)
    print("🔍 INDUSTRIAL RAG SETUP VERIFICATION")
    print("="*50)
    
    with open("configs/config.yaml", 'r') as f:
        config = yaml.safe_load(f)

    all_pass = True
    
    # 1. Check Qdrant
    try:
        client = QdrantClient(host=config['vector_store']['host'], port=config['vector_store']['port'])
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        if config['vector_store']['collection_name'] in collection_names:
            count = client.count(collection_name=config['vector_store']['collection_name']).count
            print(f"✅ Qdrant running ({count} chunks indexed)")
        else:
            print(f"❌ Qdrant running but collection '{config['vector_store']['collection_name']}' missing")
            all_pass = False
    except Exception as e:
        # Check local qdrant
        if os.path.exists("./qdrant_data"):
             print(f"✅ Qdrant using local storage at ./qdrant_data")
        else:
            print(f"❌ Qdrant not reachable at {config['vector_store']['host']}:{config['vector_store']['port']}")
            print("   Fix: docker-compose up -d qdrant")
            all_pass = False

    # 2. Check Ollama
    try:
        resp = httpx.get(f"{config['llm']['base_url']}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            print(f"✅ Ollama running")
            models = [m['name'] for m in resp.json().get('models', [])]
            if config['llm']['model'] in models or any(config['llm']['model'] in m for m in models):
                 print(f"✅ Model {config['llm']['model']} available")
            else:
                 print(f"❌ Model {config['llm']['model']} missing in Ollama")
                 print(f"   Fix: ollama pull {config['llm']['model']}")
                 all_pass = False
        else:
            print(f"❌ Ollama running but returned status {resp.status_code}")
            all_pass = False
    except Exception:
        print(f"❌ Ollama not reachable at {config['llm']['base_url']}")
        print("   Fix: Install Ollama and run 'ollama serve'")
        all_pass = False

    # 3. Check packages
    required_pkgs = ['llama_index', 'qdrant_client', 'ragas', 'mlflow', 'fastapi', 'gradio']
    missing_pkgs = []
    for pkg in required_pkgs:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing_pkgs.append(pkg)
    
    if not missing_pkgs:
        print(f"✅ All core packages installed")
    else:
        print(f"❌ Missing packages: {', '.join(missing_pkgs)}")
        print("   Fix: pip install -r requirements.txt")
        all_pass = False

    # 4. Check data
    if os.path.exists(config['data']['raw_dir']) and any(os.scandir(config['data']['raw_dir'])):
        print(f"✅ Raw data directory exists and has files")
    else:
        print(f"⚠️ Raw data directory empty. Place PDFs in {config['data']['raw_dir']}")

    print("="*50)
    if all_pass:
        print("🚀 READY TO SERVE QUERIES")
    else:
        print("⚠️ SOME CHECKS FAILED. See fixes above.")
    print("="*50 + "\n")

if __name__ == "__main__":
    verify()
