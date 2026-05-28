import gradio as gr
import httpx
import os

API_URL = "http://127.0.0.1:8000/query"
INGEST_URL = "http://127.0.0.1:8000/ingest"


API_KEY = os.getenv("API_KEY", "rag_default_secret_key_2026")


def chat_response(message, history):
    payload = {"question": str(message), "session_id": "gradio_session"}
    headers = {"X-API-Key": API_KEY}
    try:
        with httpx.Client(timeout=200.0) as client:
            response = client.post(API_URL, json=payload, headers=headers)
            if response.status_code != 200:
                return f"Error {response.status_code}: {response.text}", ""

            data = response.json()
            answer = data.get("answer", "No answer received.")
            sources = data.get("sources", [])
            latency = data.get("latency_ms", 0)

            source_info = ""
            if sources:
                source_info = "### 📄 Sources\n"
                for s in sources:
                    score = s.get("score", 0)
                    pct = int(score * 100)

                    # Color code based on percentage
                    color = "#ef4444"  # red
                    if pct > 80:
                        color = "#22c55e"  # green
                    elif pct > 60:
                        color = "#f59e0b"  # orange

                    source_info += (
                        f"* 📄 **{s.get('filename')}** — Page {s.get('page')} | "
                    )
                    source_info += f"<span style='color: {color}; font-weight: bold;'>relevance: {pct}%</span>\n"
                    source_info += f"  > *\"{s.get('text_preview', '')}...\"*\n\n"

            # Append latency to answer
            answer += f"\n\n*Latency: {latency:.2f}ms*"
            return answer, source_info

    except Exception as e:
        return f"Error: {str(e)}", ""


def upload_file(file):
    if file is None:
        return "No file uploaded."

    files = {
        "file": (os.path.basename(file.name), open(file.name, "rb"), "application/pdf")
    }
    headers = {"X-API-Key": API_KEY}
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(INGEST_URL, files=files, headers=headers)
            return response.json().get("message", "File uploaded successfully.")
    except Exception as e:
        return f"Ingestion Error: {str(e)}"


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏭 Industrial RAG Knowledge Assistant")

    with gr.Row():
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(label="Maintenance Chat", type="messages")
            msg = gr.Textbox(label="Ask a question about industrial manuals...")
            clear = gr.Button("Clear Conversation")

            sources_panel = gr.Markdown(
                "### Source Documents\n*Context will appear here after a query*"
            )

        with gr.Column(scale=1):
            file_output = gr.File(label="Upload PDF Manual")
            upload_button = gr.Button("Ingest PDF")
            status_text = gr.Textbox(label="Upload Status")

            gr.HTML("""
                <a href="http://127.0.0.1:5001" target="_blank" style="
                    display: inline-block; 
                    margin-top: 20px; 
                    padding: 10px 15px; 
                    background: #2563eb; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 8px; 
                    font-weight: bold;
                    width: 100%;
                    text-align: center;
                ">📊 View MLflow Dashboard</a>
            """)

    def user(user_message, history):
        return "", history + [{"role": "user", "content": user_message}]

    def bot(history):
        user_message = history[-1]["content"]
        bot_message, source_info = chat_response(user_message, history)
        history.append({"role": "assistant", "content": bot_message})
        return history, source_info

    msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
        bot, [chatbot], [chatbot, sources_panel]
    )

    upload_button.click(upload_file, inputs=[file_output], outputs=[status_text])
    clear.click(lambda: [], None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
