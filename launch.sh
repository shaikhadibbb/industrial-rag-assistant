#!/bin/bash
echo "🔍 Verifying Industrial RAG Assistant..."

# Create logs directory
mkdir -p logs

# Kill existing processes
lsof -ti:8000,7860,5001 | xargs kill -9 2>/dev/null
sleep 2

# Check Docker/Qdrant
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    echo "✅ Qdrant running"
else
    echo "🔄 Starting Qdrant..."
    # Check if we use local storage or docker
    if [ -d "qdrant_data" ]; then
        echo "ℹ️ Using local Qdrant storage"
    else
        docker-compose up -d qdrant
        sleep 5
    fi
fi

# Check Ollama
if curl -s http://localhost:11434 > /dev/null 2>&1; then
    echo "✅ Ollama running"
else
    echo "❌ Start Ollama: open a new terminal and run 'ollama serve'"
    exit 1
fi

# Activate venv
source venv/bin/activate
export PYTHONPATH=.

# Verify setup
python scripts/verify_setup.py

# Start backend
echo "🚀 Starting FastAPI backend..."
nohup python src/app.py > logs/app.log 2>&1 &
sleep 10

# Start UI
echo "🎨 Starting Gradio UI..."
nohup python src/ui.py > logs/ui.log 2>&1 &
sleep 3

echo ""
echo "✅ System is running!"
echo "   Chat UI:         http://localhost:7860"
echo "   API docs:        http://localhost:8000/docs"  
echo "   MLflow:          http://localhost:5001"
echo ""
echo "💡 Run evaluation:  python scripts/run_evaluation.py"
echo "💡 Push to GitHub:  git add . && git commit -m 'update' && git push"
