import httpx
import time
import sys

def verify():
    print("🚀 Running System Verification...")
    
    # 1. API Health
    try:
        r = httpx.get("http://localhost:8000/health", timeout=5)
        if r.status_code == 200:
            print("✅ API Health: OK")
        else:
            print(f"❌ API Health: Error {r.status_code}")
    except:
        print("❌ API Health: Unreachable (Start app.py first)")
        return
        
    # 2. Citation Retrieval
    try:
        t0 = time.time()
        r = httpx.post("http://localhost:8000/query", 
                       json={"question": "what is compressed air?"},
                       timeout=120)
        latency = time.time() - t0
        data = r.json()
        
        if "sources" in data and len(data["sources"]) > 0:
            print(f"✅ Citations: {len(data['sources'])} found")
            print(f"✅ Latency: {latency:.1f}s")
        else:
            print("❌ Citations: None found")
            
        if latency < 20:
            print("✅ Performance: < 20s (Passed)")
        else:
            print(f"⚠️ Performance: {latency:.1f}s (Over 20s target)")
            
    except Exception as e:
        print(f"❌ Query Test: Failed ({e})")
        
    # 3. MLflow
    try:
        r = httpx.get("http://localhost:5001", timeout=5)
        print("✅ MLflow Dashboard: OK")
    except:
        print("❌ MLflow Dashboard: Offline")

if __name__ == "__main__":
    verify()
