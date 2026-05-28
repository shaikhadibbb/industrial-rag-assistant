#!/bin/bash
echo "🔍 Verifying Industrial RAG Assistant..."

# Create logs directory
mkdir -p logs

# Kill existing processes gracefully
PIDS=$(lsof -t -i:8000,7860,5001 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "🔄 Stopping existing processes gracefully (SIGTERM)..."
    echo "$PIDS" | xargs kill -15 2>/dev/null
    
    # Wait for up to 5 seconds to check if they are shut down
    for i in {1..5}; do
        PIDS_LEFT=$(lsof -t -i:8000,7860,5001 2>/dev/null)
        if [ -z "$PIDS_LEFT" ]; then
            echo "✅ Processes shut down gracefully."
            break
        fi
        sleep 1
    done
    
    # If still running, force kill
    PIDS_LEFT=$(lsof -t -i:8000,7860,5001 2>/dev/null)
    if [ -n "$PIDS_LEFT" ]; then
        echo "⚠️ Processes still running, forcing shutdown (SIGKILL)..."
        echo "$PIDS_LEFT" | xargs kill -9 2>/dev/null
    fi
fi
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
