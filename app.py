import os
import gradio as gr
from huggingface_hub import InferenceClient

client = InferenceClient(token=os.environ.get("HF_TOKEN"))

custom_css = """
#title-area {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 12px;
    margin-bottom: 16px;
}
#title-area h1 {
    color: #00d4ff;
    font-size: 2.5em;
    margin: 0;
    letter-spacing: 4px;
}
#title-area p {
    color: #8892b0;
    margin: 4px 0 0;
    font-size: 0.85em;
    letter-spacing: 2px;
}
.sidebar {
    background: #0d1117;
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #21262d;
}
.chatbot-container {
    border-radius: 12px;
    border: 1px solid #21262d;
}
#input-row {
    margin-top: 8px;
}
#voice-row {
    margin-top: 4px;
}
"""

intro_msg = {"role": "assistant", "content": "👋 Hi! I'm **Nova**, your AI tutor. I'll remember our conversation. Type or use the 🎤 mic below to ask me anything!"}


def transcribe_audio(audio_path):
    """Transcribe audio using Whisper via HF Inference API."""
    if audio_path is None:
        return ""
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        result = client.automatic_speech_recognition(audio_bytes, model="openai/whisper-large-v3")
        return result.text if hasattr(result, "text") else str(result)
    except Exception as e:
        return f"[Transcription error: {str(e)}]"


def respond(user_text, history, subject, mode, notes):
    notes_text = notes.strip() if notes and notes.strip() else "None provided"
    system_prompt = (
        f"You are Nova, a professional AI tutor. "
        f"Subject: {subject}. Mode: {mode}. "
        f"Extra context/notes from the student: {notes_text}. "
        f"Never give the final answer directly. Instead, break every problem into clear steps. "
        f"Explain one step at a time, then ask the student if they understand before moving to the next step. "
        f"Guide them to the answer through questions and hints rather than just stating it. "
        f"When writing math, use LaTeX notation: inline with $...$ and block with $$...$$."
    )

    messages = [{"role": "system", "content": system_prompt}]

    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_text})

    response_text = ""
    try:
        for chunk in client.chat_completion(
            messages,
            model="Qwen/Qwen2.5-7B-Instruct:fastest",
            max_tokens=1024,
            stream=True,
            temperature=0.7
        ):
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                response_text += token
                yield response_text
    except Exception as e:
        yield f"⚠️ AI Error: {str(e)}. Make sure HF_TOKEN is set in your Space secrets!"


with gr.Blocks(css=custom_css) as demo:
    gr.HTML("<div id='title-area'><h1>NOVA AI</h1><p>VERSION 1.5 • HOMEWORK HELPER</p></div>")

    with gr.Row():
        with gr.Column(scale=1, elem_classes="sidebar"):
            gr.Markdown("### ⚙️ Settings")
            subject = gr.Dropdown(
                ["General 📚", "Math 🔢", "Science 🧪", "History 🏛️"],
                label="Subject",
                value="General 📚"
            )
            mode = gr.Radio(
                ["Normal", "Tutor Mode", "Quiz Mode"],
                label="Mode",
                value="Normal"
            )
            notes = gr.Textbox(
                label="Study Context",
                lines=5,
                placeholder="Paste your notes here for context..."
            )
            clear = gr.Button("🗑️ Reset Chat")

        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                value=[intro_msg],
                height=500,
                elem_classes="chatbot-container",
                show_label=False,
                latex_delimiters=[
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": "$", "right": "$", "display": False}
                ]
            )

            with gr.Row(elem_id="input-row"):
                msg = gr.MultimodalTextbox(
                    show_label=False,
                    placeholder="Ask Nova anything...",
                    scale=10,
                    elem_id="query-box",
                    file_types=[".pdf", "image"]
                )
                submit_btn = gr.Button("↑", variant="primary", scale=1)

            with gr.Row(elem_id="voice-row"):
                audio_input = gr.Audio(
                    sources=["microphone"],
                    label="🎤 Speak to Nova",
                    show_label=True
                )

    def user_fn(message, history):
        user_text = message.get("text", "") if isinstance(message, dict) else str(message)
        if not user_text.strip():
            return gr.update(value=None), history
        history = history + [{"role": "user", "content": user_text}]
        return gr.update(value=None, interactive=False), history

    def voice_fn(audio_path, history):
        """Transcribe audio and add it to history as a user message."""
        if audio_path is None:
            return history, gr.update(value=None)
        transcribed = transcribe_audio(audio_path)
        if not transcribed.strip() or transcribed.startswith("[Transcription error"):
            return history, gr.update(value=None)
        history = history + [{"role": "user", "content": f"🎤 {transcribed}"}]
        return history, gr.update(value=None)

    def bot_fn(history, subject, mode, notes):
        user_message = ""
        for m in reversed(history):
            if m.get("role") == "user":
                user_message = m["content"].lstrip("🎤 ")
                break

        if not user_message:
            yield history
            return

        history = history + [{"role": "assistant", "content": ""}]

        for chat_update in respond(user_message, history[:-1], subject, mode, notes):
            history[-1]["content"] = chat_update
            yield history

    def reset_chat():
        return [intro_msg]

    # Text submit
    submit_btn.click(
        user_fn, [msg, chatbot], [msg, chatbot]
    ).then(
        bot_fn, [chatbot, subject, mode, notes], [chatbot]
    ).then(
        lambda: gr.update(interactive=True), None, [msg]
    )

    msg.submit(
        user_fn, [msg, chatbot], [msg, chatbot]
    ).then(
        bot_fn, [chatbot, subject, mode, notes], [chatbot]
    ).then(
        lambda: gr.update(interactive=True), None, [msg]
    )

    # Voice submit — triggers when audio recording stops
    audio_input.stop_recording(
        voice_fn, [audio_input, chatbot], [chatbot, audio_input]
    ).then(
        bot_fn, [chatbot, subject, mode, notes], [chatbot]
    )

    clear.click(reset_chat, None, [chatbot])

demo.launch(server_name="0.0.0.0", server_port=10000, inline=False)
