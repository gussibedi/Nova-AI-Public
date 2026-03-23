import os
import time
import base64
import json
import uuid
import re
import gradio as gr
from huggingface_hub import InferenceClient

client = InferenceClient(token=os.environ.get("HF_TOKEN"))

# ── Nova Plus access codes (add yours here) ───────────────────────────────────
# To generate a code: just make up any string e.g. "NOVA-PLUS-2026"
# Share these privately with paying users
PLUS_CODES = set(os.environ.get("NOVA_PLUS_CODES", "NOVA-PLUS-DEMO").split(","))

custom_css = """
#title-area {
    text-align: center; padding: 20px;
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border-radius: 12px; margin-bottom: 16px;
}
#title-area h1 { color: #00d4ff; font-size: 2.5em; margin: 0; letter-spacing: 4px; }
#title-area p  { color: #8892b0; margin: 4px 0 0; font-size: 0.85em; letter-spacing: 2px; }
.history-sidebar  { background: #0d1117; border-radius: 12px; padding: 12px; border: 1px solid #21262d; }
.settings-sidebar { background: #0d1117; border-radius: 12px; padding: 16px; border: 1px solid #21262d; }
.chatbot-container { border-radius: 12px; border: 1px solid #21262d; }
#input-row { margin-top: 8px; }
#tools-row { margin-top: 6px; }
.plus-badge { color: #ffd700; font-size: 0.75em; margin-left: 4px; }
.plus-locked { opacity: 0.5; cursor: not-allowed; }
.nova-modal-overlay {
    display: none; position: fixed; top: 0; left: 0;
    width: 100%; height: 100%; background: rgba(0,0,0,0.75);
    z-index: 9999; align-items: center; justify-content: center;
}
.nova-modal-overlay.active { display: flex; }
.nova-modal {
    background: #0d1117; border: 1px solid #00d4ff;
    border-radius: 16px; padding: 32px; max-width: 420px;
    width: 90%; text-align: center; position: relative;
    box-shadow: 0 0 40px rgba(0,212,255,0.15);
}
.nova-modal h2 { color: #00d4ff; font-size: 1.6em; margin: 0 0 8px; }
.nova-modal .subtitle { color: #8892b0; font-size: 0.9em; margin-bottom: 20px; }
.nova-modal .features { text-align: left; background: #161b22; border-radius: 10px; padding: 14px 18px; margin-bottom: 20px; }
.nova-modal .features div { color: #c9d1d9; font-size: 0.88em; padding: 4px 0; }
.nova-modal .price { color: #fff; font-size: 1.1em; margin-bottom: 6px; }
.nova-modal .price span { color: #00d4ff; font-size: 1.5em; font-weight: bold; }
.nova-modal .kofi-btn {
    display: block; background: #ff5e5b; color: #fff;
    border-radius: 8px; padding: 12px; font-weight: bold;
    text-decoration: none; font-size: 1em; margin-bottom: 10px;
}
.nova-modal .code-section { margin-top: 16px; border-top: 1px solid #21262d; padding-top: 16px; }
.nova-modal .code-section p { color: #8892b0; font-size: 0.82em; margin-bottom: 8px; }
.nova-modal .code-row { display: flex; gap: 8px; }
.nova-modal .code-row input {
    flex: 1; background: #161b22; border: 1px solid #21262d;
    border-radius: 6px; padding: 8px 10px; color: #fff; font-size: 0.85em;
}
.nova-modal .code-row button {
    background: #00d4ff; color: #000; border: none;
    border-radius: 6px; padding: 8px 14px; font-weight: bold; cursor: pointer;
}
.nova-modal .close-btn {
    position: absolute; top: 12px; right: 16px;
    background: none; border: none; color: #8892b0;
    font-size: 1.4em; cursor: pointer;
}
.nova-modal .close-btn:hover { color: #fff; }
.streak-bar {
    background: #0d1117; border: 1px solid #21262d; border-radius: 10px;
    padding: 10px 16px; margin-bottom: 10px;
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
}
.streak-item { display: flex; align-items: center; gap: 6px; color: #c9d1d9; font-size: 0.85em; }
.streak-fire { font-size: 1.2em; }
.streak-num { color: #00d4ff; font-weight: bold; font-size: 1.1em; }
.goal-bar-bg { background: #161b22; border-radius: 20px; height: 8px; width: 120px; overflow: hidden; }
.goal-bar-fill { background: linear-gradient(90deg, #00d4ff, #0099cc); height: 100%; border-radius: 20px; transition: width 0.4s ease; }
.badge-popup {
    position: fixed; bottom: 24px; right: 24px; z-index: 9998;
    background: linear-gradient(135deg, #1a1a2e, #0f3460);
    border: 1px solid #ffd700; border-radius: 12px; padding: 16px 20px;
    color: #fff; font-size: 0.9em; text-align: center;
    box-shadow: 0 0 20px rgba(255,215,0,0.3);
    animation: slideIn 0.4s ease; display: none;
}
.badge-popup.show { display: block; }
@keyframes slideIn { from { transform: translateY(60px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
"""

intro_msg = {"role": "assistant", "content": "👋 Hi! I'm **Nova**, your AI tutor. Type or upload a photo 📷 of your worksheet!\n\n🌟 **Nova Plus** unlocks voice input, image upload, PDF export, and unlimited Quiz mode. Enter your code in Settings."}
CHAT_STORE_FILE = "/tmp/nova_chats.json"
MSG_LIMIT_FREE = 20


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text", "")
            if isinstance(item, str):
                return item
    return ""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_image_mime(path):
    ext = path.lower().split(".")[-1]
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","gif":"image/gif","webp":"image/webp"}.get(ext,"image/jpeg")



def load_chats():
    if os.path.exists(CHAT_STORE_FILE):
        try:
            with open(CHAT_STORE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_chats(chats):
    with open(CHAT_STORE_FILE, "w") as f:
        json.dump(chats, f)

def chat_title(history):
    for m in history:
        if m.get("role") == "user":
            text = get_text(m.get("content","")).lstrip("").strip()
            if text and text != "📷 Image uploaded":
                return text[:40] + ("..." if len(text) > 40 else "")
    return "New Chat"

def get_chat_list_html(chats, active_id=None):
    if not chats:
        return "<p style='color:#8892b0;font-size:0.8em;padding:4px;'>No saved chats yet.</p>"
    html = ""
    for cid, chat in sorted(chats.items(), key=lambda x: x[1].get("ts",0), reverse=True):
        active_style = "border-color:#00d4ff!important;" if cid == active_id else ""
        title = chat.get("title","Chat")
        html += f"""<div style='background:#161b22;border:1px solid #21262d;{active_style}border-radius:8px;padding:8px 10px;margin-bottom:5px;cursor:pointer;color:#c9d1d9;font-size:0.82em;' onclick='document.getElementById("load_chat_id_box").querySelector("textarea").value="{cid}";document.getElementById("load_chat_trigger").click();'>📄 {title}</div>"""
    return html

def count_user_messages(history):
    return sum(1 for m in history if m.get("role") == "user")

def is_plus(code):
    return code and code.strip() in PLUS_CODES

def detect_frustration(text):
    """Simple keyword-based frustration detection."""
    frustration_words = ["i don't get it", "i dont get it", "confused", "stuck", "help",
                         "frustrated", "annoying", "hard", "difficult", "don't understand",
                         "dont understand", "makes no sense", "no idea", "lost", "ugh", "wtf"]
    text_lower = text.lower()
    return any(w in text_lower for w in frustration_words)

def ai_call(messages, max_tokens=1024, temperature=0.7):
    return client.chat_completion(
        messages,
        model="Qwen/Qwen2.5-7B-Instruct:fastest",
        max_tokens=max_tokens,
        stream=False,
        temperature=temperature
    )

def build_system_prompt(subject, mode, notes_text, frustrated=False):
    base = (
        f"You are Nova, a professional AI tutor. Subject: {subject}. "
        f"Extra context/notes from the student: {notes_text}. "
        f"When writing math, use LaTeX: inline $...$ and block $$...$$. "
        f"If an image is provided, describe it then help solve the problem shown. "
    )
    if frustrated:
        base += (
            "ENCOURAGEMENT MODE: The student seems frustrated or confused. "
            "Be extra warm, patient and encouraging. Start by validating their feelings. "
            "Simplify your explanation and use an analogy or real-world example. "
            "Remind them that struggling is normal and part of learning. "
        )
    elif mode == "Tutor Mode":
        base += (
            "TUTOR MODE: Never give the final answer. Guide the student Socratically. "
            "Ask what they think the first step is, offer hints, praise progress. "
            "If a student seems to just want the answer without trying, switch to asking "
            "'What have you tried so far?' to ensure they actually engage. "
        )
    elif mode == "Quiz Mode":
        base += (
            "QUIZ MODE: Ask the student questions to test their understanding. "
            "After each answer, tell them if they're right and explain why. "
        )
    elif mode == "Crunch Time ⚡":
        base += (
            "CRUNCH TIME MODE: The student is under time pressure. "
            "Give the direct answer immediately, then show the key steps as briefly as possible. "
            "No Socratic questions, no lengthy explanations. Just the answer and the essential steps. "
            "Format: Answer first, then steps in bullet points."
        )
    else:
        base += "Break every problem into clear steps and check understanding at each step. "
    return base


# ── Core respond (streaming) ──────────────────────────────────────────────────

def respond(user_text, image_paths, history, subject, mode, notes):
    notes_text = notes.strip() if notes and notes.strip() else "None provided"
    frustrated = detect_frustration(user_text)
    system_prompt = build_system_prompt(subject, mode, notes_text, frustrated)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = msg.get("role","")
        content = get_text(msg.get("content",""))
        if role in ("user","assistant") and content:
            messages.append({"role": role, "content": content})

    if image_paths:
        user_content = []
        for img_path in image_paths:
            try:
                b64 = encode_image(img_path)
                mime = get_image_mime(img_path)
                user_content.append({"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}})
            except Exception:
                pass
        if user_text.strip():
            # Student provided context — treat as "show your work" review
            image_prompt = (
                f"The student says: '{user_text}'. "
                f"Look carefully at their handwritten or typed work in the image. "
                f"Identify exactly where their reasoning is correct and where it goes wrong. "
                f"Be specific — say things like 'You were right until step 2, but in step 3 you forgot to...' "
                f"Do NOT just solve it from scratch. Analyze their actual attempt and guide them from there."
            )
        else:
            # No context — general problem solving
            image_prompt = (
                "Look at this image carefully. If it shows a student's handwritten work or attempt, "
                "identify what they did correctly and where they made errors, step by step. "
                "If it's a problem with no attempt shown, break it down step by step and guide the student to the answer."
            )
        user_content.append({"type":"text","text": image_prompt})
        messages.append({"role":"user","content":user_content})
        model = "Qwen/Qwen2-VL-7B-Instruct:fastest"
    else:
        messages.append({"role":"user","content":user_text})
        model = "Qwen/Qwen2.5-7B-Instruct:fastest"

    start_time = time.time()
    response_text = ""
    thinking_yielded = False

    try:
        for chunk in client.chat_completion(messages, model=model, max_tokens=1024, stream=True, temperature=0.7):
            if not thinking_yielded and (time.time() - start_time) > 3:
                yield {"role":"assistant","content":"🤔 Working through this...","metadata":{"title":"💭 Nova is thinking..."}}, ""
                thinking_yielded = True
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
                yield None, response_text
    except Exception as e:
        yield None, f"⚠️ AI Error: {str(e)}. Make sure HF_TOKEN is set in Space secrets!"


# ── Tool functions ────────────────────────────────────────────────────────────

def generate_flashcards(history):
    if len(history) < 2:
        return "❌ Have a conversation with Nova first, then generate flashcards!"
    convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
    messages = [
        {"role":"system","content":"Generate exactly 5 flashcards. Format:\nQ1: [question]\nA1: [answer]\n...up to Q5/A5. Be concise."},
        {"role":"user","content":f"Generate 5 flashcards from:\n\n{convo[:3000]}"}
    ]
    try:
        resp = ai_call(messages, max_tokens=600, temperature=0.5)
        raw = resp.choices[0].message.content.strip()
        lines = raw.split("\n")
        cards, q = [], ""
        for line in lines:
            line = line.strip()
            if line.startswith("Q") and ":" in line:
                q = line.split(":",1)[1].strip()
            elif line.startswith("A") and ":" in line and q:
                cards.append((q, line.split(":",1)[1].strip()))
                q = ""
        if not cards:
            return f"## 📇 Flashcards\n\n{raw}"
        result = "## 📇 Flashcards\n\n"
        for i, (q, a) in enumerate(cards, 1):
            result += f"**Card {i}**\n- ❓ {q}\n- ✅ {a}\n\n"
        return result
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def generate_quiz(history):
    if len(history) < 2:
        return "❌ Have a conversation first!"
    convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
    messages = [
        {"role":"system","content":"Create a 4-question MCQ quiz. Format each as:\n[Q1] Question\na) opt  b) opt  c) opt  d) opt\nAnswer: x) correct\nExplanation: reason\n\nRepeat for Q2-Q4."},
        {"role":"user","content":f"Quiz from:\n\n{convo[:3000]}"}
    ]
    try:
        resp = ai_call(messages, max_tokens=800, temperature=0.5)
        return "## 📝 Practice Quiz\n\n" + resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def cleanup_notes(notes_text):
    if not notes_text or not notes_text.strip():
        return "❌ Paste notes in the Study Context box first!"
    messages = [
        {"role":"system","content":"Reformat messy notes into a clean structured outline with bold title, ## headers, bullet points, and a 2-sentence summary at the bottom. Keep all info."},
        {"role":"user","content":f"Clean up:\n\n{notes_text}"}
    ]
    try:
        resp = ai_call(messages, max_tokens=800, temperature=0.4)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def get_citations(history):
    if len(history) < 2:
        return "❌ Have a conversation first!"
    convo = "\n".join([f"NOVA: {get_text(m.get('content',''))}" for m in history if m.get("role") == "assistant"])
    messages = [
        {"role":"system","content":"Extract 3 factual claims and provide a search URL for each. Format:\n**Claim:** [claim]\n**Search:** [URL]\n\nRepeat for 3 claims."},
        {"role":"user","content":f"Find sources for:\n\n{convo[:2000]}"}
    ]
    try:
        resp = ai_call(messages, max_tokens=500, temperature=0.3)
        return "## 🔗 Source Verification\n\n" + resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def export_pdf(history):
    """Export chat to a PDF study guide."""
    if len(history) < 2:
        return None, "❌ Have a conversation first!"
    try:
        from fpdf import FPDF
        import tempfile

        # Generate a clean study guide with AI first
        convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
        messages = [
            {"role":"system","content":"Convert this tutoring session into a clean study guide with: Title, Key Concepts (bullet points), Step-by-Step Solutions, and a Summary. Use plain text only, no markdown symbols."},
            {"role":"user","content":f"Make a study guide from:\n\n{convo[:4000]}"}
        ]
        resp = ai_call(messages, max_tokens=1200, temperature=0.4)
        guide_text = resp.choices[0].message.content.strip()

        # Build PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Nova AI - Study Guide", ln=True, align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Generated by Nova AI", ln=True, align="C")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 11)

        for line in guide_text.split("\n"):
            line = line.strip()
            if not line:
                pdf.ln(3)
                continue
            # Simple encoding — replace unsupported chars
            safe_line = line.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 6, safe_line)

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="/tmp/nova_study_")
        pdf.output(tmp.name)
        return tmp.name, "✅ PDF ready — click Download!"
    except ImportError:
        return None, "⚠️ fpdf2 not installed. Add 'fpdf2' to requirements.txt!"
    except Exception as e:
        return None, f"⚠️ PDF Error: {str(e)}"


def update_streak(streak_data):
    """Update streak and daily goal, return new state and HTML."""
    import datetime
    today = str(datetime.date.today())
    data = dict(streak_data)

    if data.get("last_date") != today:
        # New day
        yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
        if data.get("last_date") == yesterday:
            data["streak"] = data.get("streak", 0) + 1
        elif data.get("last_date") != today:
            data["streak"] = 1  # reset if missed a day
        data["problems_today"] = 0
        data["last_date"] = today

    data["problems_today"] = data.get("problems_today", 0) + 1
    goal = data.get("daily_goal", 3)
    pct = min(100, int((data["problems_today"] / goal) * 100))

    # Badge logic
    badge_html = ""
    popup_html = ""
    badges = data.get("badges", [])

    if data["problems_today"] == goal and "daily_goal" not in badges:
        badges.append("daily_goal")
        badge_html = "🏆"
        popup_html = f"""<div class='badge-popup show' id='badge-popup'>
            🏆 Daily Goal Hit!<br><small>You solved {goal} problems today!</small>
        </div>
        <script>setTimeout(()=>{{document.getElementById('badge-popup').classList.remove('show')}},4000)</script>"""

    if data["streak"] >= 3 and "streak_3" not in badges:
        badges.append("streak_3")
        badge_html = "🔥"
        popup_html = """<div class='badge-popup show' id='badge-popup'>
            🔥 3-Day Streak!<br><small>Keep it up — you're on fire!</small>
        </div>
        <script>setTimeout(()=>{{document.getElementById('badge-popup').classList.remove('show')}},4000)</script>"""

    if data["streak"] >= 7 and "streak_7" not in badges:
        badges.append("streak_7")
        badge_html = "⭐"
        popup_html = """<div class='badge-popup show' id='badge-popup'>
            ⭐ 7-Day Streak!<br><small>A full week! You earned a Nova Plus day!</small>
        </div>
        <script>setTimeout(()=>{{document.getElementById('badge-popup').classList.remove('show')}},4000)</script>"""

    data["badges"] = badges

    html = f"""
    <div class='streak-bar'>
        <div class='streak-item'><span class='streak-fire'>🔥</span><span>Streak:</span><span class='streak-num'>{data['streak']}</span><span>days</span></div>
        <div class='streak-item'>
            <span>Daily goal:</span>
            <div class='goal-bar-bg'><div class='goal-bar-fill' style='width:{pct}%'></div></div>
            <span>{data['problems_today']}/{goal}</span>
        </div>
        <div class='streak-item'>{badge_html}</div>
    </div>
    {popup_html}
    """
    return data, html


def generate_exit_ticket(history):
    """Generate a 3-bullet exit ticket summary when saving a chat."""
    if len(history) < 2:
        return ""
    convo = "\n".join([
        f"{m['role'].upper()}: {get_text(m.get('content',''))}"
        for m in history if m.get("role") in ("user","assistant")
    ])
    messages = [
        {"role":"system","content":(
            "You are a classroom assistant. Generate exactly 3 bullet points summarizing "
            "the key takeaways from this tutoring session. Format as:\n"
            "## 📋 Session Exit Ticket\n\n"
            "**What we covered today:**\n"
            "• [key concept 1]\n"
            "• [key concept 2]\n"
            "• [key concept 3]\n\n"
            "**Remember:** [one sentence the student should remember]\n\n"
            "Keep it concise and student-friendly."
        )},
        {"role":"user","content":f"Summarize this session:\n\n{convo[:3000]}"}
    ]
    try:
        resp = ai_call(messages, max_tokens=300, temperature=0.4)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Could not generate summary: {str(e)}"


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks() as demo:
    gr.HTML("<div id='title-area'><h1>NOVA AI</h1><p>VERSION 4.1 • SMART TUTOR</p></div>")
    streak_display = gr.HTML(
        "<div class='streak-bar'>"
        "<div class='streak-item'><span class='streak-fire'>&#128293;</span><span>Streak:</span><span class='streak-num' id='streak-count'>0</span><span>days</span></div>"
        "<div class='streak-item'><span>Daily goal:</span><div class='goal-bar-bg'><div class='goal-bar-fill' id='goal-fill' style='width:0%'></div></div><span id='goal-text'>0/3</span></div>"
        "<div class='streak-item' id='badge-area'></div>"
        "</div><div class='badge-popup' id='badge-popup'></div>"
    )

    # ── Nova Plus banner (visible to free users) ──────────────────────────────
    plus_banner = gr.HTML(
        """<div id='plus-banner' style='background:linear-gradient(90deg,#1a1a2e,#0f3460);border:1px solid #00d4ff;border-radius:10px;padding:12px 20px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>
        <div style='color:#fff;font-size:0.95em;'>🌟 <strong>Nova Plus</strong> — unlock voice input, image upload, PDF export     gr.HTML("<div id='title-area'><h1>NOVA AI</h1><p>VERSION 4.1 • SMART TUTOR</p></div>")
    streak_display = gr.HTML(
        "<div class='streak-bar'>"
        "<div class='streak-item'><span class='streak-fire'>&#128293;</span><span>Streak:</span><span class='streak-num' id='streak-count'>0</span><span>days</span></div>"
        "<div class='streak-item'><span>Daily goal:</span><div class='goal-bar-bg'><div class='goal-bar-fill' id='goal-fill' style='width:0%'></div></div><span id='goal-text'>0/3</span></div>"
        "<div class='streak-item' id='badge-area'></div>"
        "</div><div class='badge-popup' id='badge-popup'></div>"
    )amp; unlimited Quiz Mode</div>
        <div style='display:flex;gap:8px;align-items:center;'>
            <input id='banner-code-input' type='password' placeholder='Enter Plus code...' style='background:#0d1117;border:1px solid #00d4ff;border-radius:6px;padding:6px 10px;color:#fff;font-size:0.85em;width:160px;' />
            <button onclick='(function(){ var code=document.getElementById('banner-code-input').value; var tb=document.querySelector('#plus-code-box textarea'); if(tb){tb.value=code;tb.dispatchEvent(new Event('input',{bubbles:true}));} setTimeout(function(){document.getElementById('plus-activate-trigger').click();},100); })()' style='background:#00d4ff;color:#000;border:none;border-radius:6px;padding:6px 14px;font-weight:bold;cursor:pointer;font-size:0.85em;'>Activate</button>
            <a href='https://ko-fi.com/guranshb' target='_blank' style='background:#ff5e5b;color:#fff;border-radius:6px;padding:6px 14px;font-weight:bold;text-decoration:none;font-size:0.85em;'>Get Plus →</a>
        </div>
        </div>"""
    )

    chat_store     = gr.State(load_chats())
    active_chat_id = gr.State(None)
    last_msg_state = gr.State({})
    plus_state     = gr.State(False)
    streak_state   = gr.State({"streak": 0, "problems_today": 0, "daily_goal": 3, "last_date": "", "badges": []})

    with gr.Row():

        # ── Chat history sidebar ──────────────────────────────────────────────
        with gr.Column(scale=1, elem_classes="history-sidebar"):
            gr.Markdown("### 💬 Chats")
            new_chat_btn  = gr.Button("＋ New Chat",  variant="secondary", size="sm")
            save_chat_btn = gr.Button("💾 Save Chat", variant="secondary", size="sm")
            chat_list_html = gr.HTML("<p style='color:#8892b0;font-size:0.8em;padding:4px;'>No saved chats yet.</p>")
            load_chat_id  = gr.Textbox(visible=False, elem_id="load_chat_id_box")
            load_chat_btn = gr.Button(visible=False,  elem_id="load_chat_trigger")

        # ── Main chat area ────────────────────────────────────────────────────
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                value=[intro_msg], height=400,
                elem_classes="chatbot-container", show_label=False,
                latex_delimiters=[
                    {"left":"$$","right":"$$","display":True},
                    {"left":"$","right":"$","display":False}
                ]
            )

            with gr.Row(elem_id="input-row"):
                msg = gr.MultimodalTextbox(
                    show_label=False,
                    placeholder="Ask Nova anything, or upload a photo of your worksheet...",
                    scale=10, elem_id="query-box", file_types=[".pdf","image"]
                )
                submit_btn = gr.Button("↑", variant="primary", scale=1)

            # Voice input removed - unreliable on HF free tier

            # Tool buttons
            with gr.Row(elem_id="tools-row"):
                flashcard_btn = gr.Button("📇 Flashcards",   variant="secondary", size="sm")
                quiz_btn      = gr.Button("📝 Quiz Me ✨",    variant="secondary", size="sm")
                citation_btn  = gr.Button("🔗 Citations",    variant="secondary", size="sm")
                pdf_btn       = gr.Button("📄 Export PDF ✨", variant="secondary", size="sm")

            tool_output  = gr.Markdown(visible=False)
            pdf_download = gr.File(visible=False, label="📄 Download Study Guide PDF")

            # YouTube analysis (Plus)

        # ── Settings sidebar ──────────────────────────────────────────────────
        with gr.Column(scale=1, elem_classes="settings-sidebar"):
            gr.Markdown("### ⚙️ Settings")
            subject = gr.Dropdown(
                ["General 📚","Math 🔢","Science 🧪","History 🏛️"],
                label="Subject", value="General 📚"
            )
            mode = gr.Radio(
                ["Normal","Tutor Mode","Quiz Mode","Crunch Time ⚡"],
                label="Mode", value="Normal"
            )
            notes = gr.Textbox(label="Study Context / Notes", lines=5, placeholder="Paste your notes here...")
            cleanup_btn = gr.Button("✨ Clean Up Notes", variant="secondary", size="sm")
            gr.Markdown("---")
            gr.Markdown("### 🌟 Nova Plus")
            plus_code_input = gr.Textbox(show_label=False, placeholder="Enter Plus access code...", type="password", elem_id="plus-code-box")
            plus_activate_btn = gr.Button("Activate", variant="primary", size="sm", elem_id="plus-activate-trigger")
            plus_status = gr.Markdown("<p style='color:#8892b0;font-size:0.8em;'>Free tier: 20 messages/session</p>")

    # ── Event handlers ────────────────────────────────────────────────────────

    def activate_plus(code, history):
        if is_plus(code):
            return True, "✅ **Nova Plus activated!** 🌟 All features unlocked.", gr.update(visible=False)
        return False, "❌ Invalid code. Visit [ko-fi.com/guranshb](https://ko-fi.com/guranshb) to get Nova Plus!", gr.update(visible=True)

    def user_fn(message, history, plus):
        user_text = message.get("text","") if isinstance(message, dict) else str(message)
        files     = message.get("files",[]) if isinstance(message, dict) else []
        if not user_text.strip() and not files:
            return gr.update(value=None), history, {}
        # Message limit for free users
        if not plus and count_user_messages(history) >= MSG_LIMIT_FREE:
            history = history + [{"role":"assistant","content":f"⚠️ You've reached the **{MSG_LIMIT_FREE} message limit**. Upgrade to **Nova Plus** for unlimited messages — click the banner at the top! 🌟"}]
            return gr.update(value=None), history, {}
        # Block image uploads for free users
        if files and not plus:
            history = history + [{"role":"assistant","content":"📷 Image upload is **Nova Plus** only. Click **Upgrade to Nova Plus** in the banner above to unlock! 🌟"}]
            return gr.update(value=None), history, {}
        display = user_text if user_text.strip() else "📷 Image uploaded"
        history  = history + [{"role":"user","content":display}]
        raw      = {"text": user_text, "files": files}
        return gr.update(value=None, interactive=False), history, raw



    def bot_fn(last_msg, history, subject, mode, notes, streak_data):
        user_message = ""
        for m in reversed(history):
            if m.get("role") == "user":
                user_message = get_text(m.get("content","")).lstrip("")
                if user_message == "📷 Image uploaded":
                    user_message = ""
                break

        image_paths = []
        if isinstance(last_msg, dict):
            for f in last_msg.get("files",[]):
                path = f.get("path", f) if isinstance(f, dict) else f
                if path:
                    image_paths.append(path)

        if not user_message and not image_paths:
            yield history
            return

        thinking_block = None
        answer_text    = ""
        history        = list(history)

        for thought, answer in respond(user_message, image_paths, history[:-1], subject, mode, notes):
            if thought is not None:
                thinking_block = thought
                yield history + [thinking_block]
            if answer:
                answer_text = answer
                if thinking_block:
                    yield history + [thinking_block, {"role":"assistant","content":answer_text}]
                else:
                    yield history + [{"role":"assistant","content":answer_text}]

    def bot_fn_streak(last_msg, history, subject, mode, notes, streak_data):
        """Wrapper that updates streak after bot_fn completes."""
        final_history = history
        for h in bot_fn(last_msg, history, subject, mode, notes, streak_data):
            final_history = h
            yield h, streak_data, gr.update()
        # Update streak after response completes
        new_streak, streak_html = update_streak(streak_data)
        yield final_history, new_streak, gr.update(value=streak_html)

    def save_chat_fn(history, chats, active_id):
        if len(history) <= 1:
            return chats, active_id, gr.update(), gr.update()
        cid = active_id if active_id else str(uuid.uuid4())[:8]
        chats = dict(chats)
        chats[cid] = {"title": chat_title(history), "history": history, "ts": time.time()}
        save_chats(chats)
        # Generate exit ticket summary
        summary = generate_exit_ticket(history)
        return chats, cid, gr.update(value=get_chat_list_html(chats, cid)), gr.update(value=summary, visible=True)

    def new_chat_fn(history, chats, active_id):
        updated = dict(chats)
        if len(history) > 1:
            cid = active_id if active_id else str(uuid.uuid4())[:8]
            updated[cid] = {"title": chat_title(history), "history": history, "ts": time.time()}
            save_chats(updated)
        return [intro_msg], updated, None, gr.update(value=get_chat_list_html(updated, None))

    def load_chat_fn(cid, chats):
        if not cid or cid not in chats:
            return gr.update(), gr.update(), gr.update()
        return chats[cid]["history"], cid, gr.update(value=get_chat_list_html(chats, cid))

    def quiz_fn_gated(history, plus):
        if not plus:
            return gr.update(value="<script>showPlusModal()</script>🌟 **Quiz Mode is Nova Plus only.** Upgrade to unlock!", visible=True)
        return gr.update(value=generate_quiz(history), visible=True)

    def pdf_fn_gated(history, plus):
        if not plus:
            return gr.update(visible=False), gr.update(value="<script>showPlusModal()</script>🌟 **PDF Export is Nova Plus only.** Upgrade to unlock!", visible=True)
        path, msg_txt = export_pdf(history)
        if path:
            return gr.update(value=path, visible=True), gr.update(value=msg_txt, visible=True)
        return gr.update(visible=False), gr.update(value=msg_txt, visible=True)

    def cleanup_fn(notes_text):
        result = cleanup_notes(notes_text)
        return result, gr.update(value=result, visible=True)

    # Wire events
    plus_activate_btn.click(activate_plus, [plus_code_input, chatbot], [plus_state, plus_status, plus_banner])

    submit_btn.click(
        user_fn, [msg, chatbot, plus_state], [msg, chatbot, last_msg_state]
    ).then(
        bot_fn_streak, [last_msg_state, chatbot, subject, mode, notes, streak_state], [chatbot, streak_state, streak_display]
    ).then(
        lambda: gr.update(interactive=True), None, [msg]
    )

    msg.submit(
        user_fn, [msg, chatbot, plus_state], [msg, chatbot, last_msg_state]
    ).then(
        bot_fn_streak, [last_msg_state, chatbot, subject, mode, notes, streak_state], [chatbot, streak_state, streak_display]
    ).then(
        lambda: gr.update(interactive=True), None, [msg]
    )



    save_chat_btn.click(save_chat_fn, [chatbot, chat_store, active_chat_id], [chat_store, active_chat_id, chat_list_html, tool_output])
    new_chat_btn.click(new_chat_fn,   [chatbot, chat_store, active_chat_id], [chatbot, chat_store, active_chat_id, chat_list_html])
    load_chat_btn.click(load_chat_fn, [load_chat_id, chat_store],            [chatbot, active_chat_id, chat_list_html])

    flashcard_btn.click(lambda h: gr.update(value=generate_flashcards(h), visible=True), [chatbot], [tool_output])
    quiz_btn.click(quiz_fn_gated,     [chatbot, plus_state], [tool_output])
    citation_btn.click(lambda h: gr.update(value=get_citations(h), visible=True), [chatbot], [tool_output])
    pdf_btn.click(pdf_fn_gated,       [chatbot, plus_state], [pdf_download, tool_output])
    cleanup_btn.click(cleanup_fn,     [notes], [notes, tool_output])

demo.launch(css=custom_css)
