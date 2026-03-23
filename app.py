import os
import time
import base64
import json
import uuid
import re
import datetime
import stripe
import gradio as gr
from huggingface_hub import InferenceClient

client = InferenceClient(token=os.environ.get("HF_TOKEN"))
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
RENDER_URL = "https://nova-ai-public.onrender.com"
PLUS_CODES = set(os.environ.get("NOVA_PLUS_CODES", "NOVA-PLUS-DEMO").split(","))
CHAT_STORE_FILE = "/tmp/nova_chats.json"
MSG_LIMIT_FREE = 20

custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
* { font-family: 'Space Grotesk', sans-serif; box-sizing: border-box; }
body, .gradio-container { background: #080c14 !important; }
#title-area {
    text-align: center; padding: 28px 20px 20px;
    background: linear-gradient(135deg, #0a0f1e 0%, #0d1f3c 50%, #0a0f1e 100%);
    border-radius: 16px; margin-bottom: 14px;
    border: 1px solid rgba(0,180,255,0.15);
}
#title-area h1 { color: #fff; font-size: 2.8em; margin: 0; letter-spacing: 8px; font-weight: 700; text-shadow: 0 0 30px rgba(0,180,255,0.4); }
#title-area h1 span { color: #00b4ff; }
#title-area p { color: #4a6fa5; margin: 6px 0 0; font-size: 0.78em; letter-spacing: 3px; text-transform: uppercase; }
.plus-banner {
    background: linear-gradient(90deg, #0a1628, #0d2040, #0a1628);
    border: 1px solid rgba(0,180,255,0.3); border-radius: 12px;
    padding: 12px 20px; margin-bottom: 14px;
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;
}
.plus-banner-text { color: #a8c4e0; font-size: 0.88em; }
.plus-banner-text strong { color: #00b4ff; }
.plus-banner-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.banner-input { background: #0d1117; border: 1px solid rgba(0,180,255,0.3); border-radius: 8px; padding: 7px 12px; color: #fff; font-size: 0.82em; width: 150px; outline: none; }
.banner-activate-btn { background: #00b4ff; color: #000; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 600; cursor: pointer; font-size: 0.82em; }
.banner-getplus-btn { background: transparent; color: #00b4ff; border: 1px solid #00b4ff; border-radius: 8px; padding: 7px 14px; font-weight: 600; font-size: 0.82em; text-decoration: none; }
.streak-bar { background: #0a0f1e; border: 1px solid #161f30; border-radius: 12px; padding: 10px 18px; margin-bottom: 12px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.streak-item { display: flex; align-items: center; gap: 8px; color: #4a6fa5; font-size: 0.82em; }
.streak-num { color: #00b4ff; font-weight: 700; font-size: 1.15em; }
.goal-bar-bg { background: #161f30; border-radius: 20px; height: 6px; width: 100px; overflow: hidden; }
.goal-bar-fill { background: linear-gradient(90deg, #00b4ff, #0066cc); height: 100%; border-radius: 20px; transition: width 0.5s ease; }
.history-sidebar { background: #0a0f1e; border-radius: 14px; padding: 14px; border: 1px solid #161f30; }
.settings-sidebar { background: #0a0f1e; border-radius: 14px; padding: 16px; border: 1px solid #161f30; }
.chatbot-container { border-radius: 14px !important; border: 1px solid #161f30 !important; background: #0a0f1e !important; }
#input-row { margin-top: 10px; }
#tools-row { margin-top: 8px; }
.section-label { color: #4a6fa5; font-size: 0.72em; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px; margin-top: 14px; }
.nova-modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
.nova-modal-overlay.active { display: flex; }
.nova-modal { background: #0a0f1e; border: 1px solid rgba(0,180,255,0.3); border-radius: 20px; padding: 36px; max-width: 440px; width: 92%; text-align: center; position: relative; box-shadow: 0 0 60px rgba(0,180,255,0.1); }
.nova-modal h2 { color: #fff; font-size: 1.7em; margin: 0 0 6px; font-weight: 700; }
.nova-modal .subtitle { color: #4a6fa5; font-size: 0.88em; margin-bottom: 22px; }
.nova-modal .features { text-align: left; background: #0d1428; border-radius: 12px; padding: 14px 18px; margin-bottom: 22px; border: 1px solid #161f30; }
.nova-modal .features div { color: #a8c4e0; font-size: 0.86em; padding: 5px 0; }
.nova-modal .price { color: #fff; font-size: 1em; margin-bottom: 14px; }
.nova-modal .price .amount { color: #00b4ff; font-size: 2em; font-weight: 700; }
.nova-modal .kofi-btn { display: block; background: #00b4ff; color: #000; border-radius: 10px; padding: 13px; font-weight: 700; text-decoration: none; font-size: 1em; margin-bottom: 10px; }
.nova-modal .code-section { margin-top: 18px; border-top: 1px solid #161f30; padding-top: 18px; }
.nova-modal .code-section p { color: #4a6fa5; font-size: 0.82em; margin-bottom: 10px; }
.nova-modal .code-row { display: flex; gap: 8px; }
.nova-modal .code-row input { flex: 1; background: #0d1428; border: 1px solid #161f30; border-radius: 8px; padding: 9px 12px; color: #fff; font-size: 0.85em; outline: none; }
.nova-modal .code-row button { background: #00b4ff; color: #000; border: none; border-radius: 8px; padding: 9px 16px; font-weight: 700; cursor: pointer; }
.nova-modal .close-btn { position: absolute; top: 14px; right: 18px; background: none; border: none; color: #4a6fa5; font-size: 1.5em; cursor: pointer; }
.nova-modal .close-btn:hover { color: #fff; }
.badge-popup { position: fixed; bottom: 28px; right: 28px; z-index: 9998; background: #0a0f1e; border: 1px solid #ffd700; border-radius: 14px; padding: 16px 22px; color: #fff; font-size: 0.88em; text-align: center; box-shadow: 0 0 30px rgba(255,215,0,0.2); animation: slideUp 0.4s ease; display: none; }
.badge-popup.show { display: block; }
@keyframes slideUp { from { transform: translateY(80px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
"""

intro_msg = {
    "role": "assistant",
    "content": (
        "Hi! I'm **Nova**, your AI tutor.\n\n"
        "Type a question or upload a photo of your worksheet and I'll walk you through it step by step.\n\n"
        "🌟 **Nova Plus** unlocks image upload, PDF export, and unlimited Quiz Mode."
    )
}


def get_text(content):
    if isinstance(content, str): return content
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text": return item.get("text", "")
            if isinstance(item, str): return item
    return ""

def encode_image(path):
    with open(path, "rb") as f: return base64.b64encode(f.read()).decode("utf-8")

def get_image_mime(path):
    ext = path.lower().split(".")[-1]
    return {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","gif":"image/gif","webp":"image/webp"}.get(ext,"image/jpeg")

def load_chats():
    if os.path.exists(CHAT_STORE_FILE):
        try:
            with open(CHAT_STORE_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_chats(chats):
    with open(CHAT_STORE_FILE, "w") as f: json.dump(chats, f)

def chat_title(history):
    for m in history:
        if m.get("role") == "user":
            text = get_text(m.get("content","")).strip()
            if text and text != "Image uploaded": return text[:40] + ("..." if len(text) > 40 else "")
    return "New Chat"

def get_chat_list_html(chats, active_id=None):
    if not chats: return "<p style='color:#4a6fa5;font-size:0.8em;padding:4px;'>No saved chats yet.</p>"
    html = ""
    for cid, chat in sorted(chats.items(), key=lambda x: x[1].get("ts",0), reverse=True):
        active = "border-color:rgba(0,180,255,0.6)!important;background:#0d1f3c!important;" if cid == active_id else ""
        title = chat.get("title","Chat")
        html += f"<div style='background:#0d1428;border:1px solid #161f30;{active}border-radius:10px;padding:9px 12px;margin-bottom:6px;cursor:pointer;color:#a8c4e0;font-size:0.82em;' onclick='document.getElementById(\"load_chat_id_box\").querySelector(\"textarea\").value=\"{cid}\";document.getElementById(\"load_chat_trigger\").click();'>📄 {title}</div>"
    return html

def count_user_messages(history):
    return sum(1 for m in history if m.get("role") == "user")

def is_plus(code):
    return code and code.strip() in PLUS_CODES

def detect_frustration(text):
    words = ["i don't get it","i dont get it","confused","stuck","frustrated","annoying",
             "don't understand","dont understand","makes no sense","no idea","lost","ugh","wtf","i give up"]
    return any(w in text.lower() for w in words)

def ai_call(messages, max_tokens=1024, temperature=0.7):
    return client.chat_completion(messages, model="Qwen/Qwen2.5-7B-Instruct:fastest",
                                  max_tokens=max_tokens, stream=False, temperature=temperature)

def build_system_prompt(subject, mode, notes_text, frustrated=False):
    base = (f"You are Nova, a professional AI tutor. Subject: {subject}. "
            f"Extra context: {notes_text}. Use LaTeX for math: inline $...$ and block $$...$$. ")
    if frustrated:
        base += "ENCOURAGEMENT MODE: Student is frustrated. Be warm and validating. Use a real-world analogy. Remind them struggling is normal. "
    elif mode == "Tutor Mode":
        base += "TUTOR MODE: Never give the final answer. Guide Socratically. Ask 'What do you think the first step is?' Only reveal answer after 3+ attempts. "
    elif mode == "Quiz Mode":
        base += "QUIZ MODE: Test the student with questions. After each answer explain if correct and why. "
    elif mode == "Crunch Time":
        base += "CRUNCH TIME MODE: Give the direct answer immediately, then key steps as brief bullets. No Socratic questions. "
    else:
        base += "Break every problem into clear numbered steps and check understanding at each one. "
    return base

def respond(user_text, image_paths, history, subject, mode, notes):
    notes_text = notes.strip() if notes and notes.strip() else "None provided"
    frustrated = detect_frustration(user_text)
    system_prompt = build_system_prompt(subject, mode, notes_text, frustrated)
    messages = [{"role": "system", "content": system_prompt}]
    for m in history:
        role = m.get("role","")
        content = get_text(m.get("content",""))
        if role in ("user","assistant") and content:
            messages.append({"role": role, "content": content})
    if image_paths:
        user_content = []
        for img_path in image_paths:
            try:
                b64 = encode_image(img_path)
                mime = get_image_mime(img_path)
                user_content.append({"type":"image_url","image_url":{"url":f"data:{mime};base64,{b64}"}})
            except: pass
        image_prompt = (f"The student says: '{user_text}'. Look carefully at their work in the image. "
                        f"Identify exactly where their reasoning is correct and where it goes wrong. "
                        f"Say things like 'You were right until step 2, but in step 3 you forgot to...' "
                        f"Do NOT solve from scratch. Analyze their actual attempt.") if user_text.strip() else (
                        "Look at this image. If it shows student work, identify what they did correctly and where they made errors. "
                        "If it's just a problem, break it down step by step.")
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
                yield {"role":"assistant","content":"Working through this...","metadata":{"title":"Nova is thinking..."}}, ""
                thinking_yielded = True
            if chunk.choices[0].delta and chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
                yield None, response_text
    except Exception as e:
        yield None, f"Error: {str(e)}"

def generate_flashcards(history):
    if len(history) < 2: return "Have a conversation with Nova first!"
    convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
    try:
        resp = ai_call([{"role":"system","content":"Generate exactly 5 flashcards.\nFormat:\nQ1: [question]\nA1: [answer]\n...up to Q5/A5."},
                        {"role":"user","content":f"Flashcards from:\n\n{convo[:3000]}"}], max_tokens=600, temperature=0.5)
        raw = resp.choices[0].message.content.strip()
        lines = raw.split("\n")
        cards, q = [], ""
        for line in lines:
            line = line.strip()
            if line.startswith("Q") and ":" in line: q = line.split(":",1)[1].strip()
            elif line.startswith("A") and ":" in line and q:
                cards.append((q, line.split(":",1)[1].strip())); q = ""
        if not cards: return f"## Flashcards\n\n{raw}"
        result = "## Flashcards\n\n"
        for i, (q, a) in enumerate(cards, 1): result += f"**Card {i}**\n- Q: {q}\n- A: {a}\n\n"
        return result
    except Exception as e: return f"Error: {str(e)}"

def generate_quiz(history):
    if len(history) < 2: return "Have a conversation first!"
    convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
    try:
        resp = ai_call([{"role":"system","content":"Create a 4-question MCQ quiz.\nFormat:\n[Q1] Question\na) b) c) d)\nAnswer: x)\nExplanation: reason\nRepeat for Q2-Q4."},
                        {"role":"user","content":f"Quiz from:\n\n{convo[:3000]}"}], max_tokens=800, temperature=0.5)
        return "## Practice Quiz\n\n" + resp.choices[0].message.content.strip()
    except Exception as e: return f"Error: {str(e)}"

def cleanup_notes(notes_text):
    if not notes_text or not notes_text.strip(): return "Paste notes in the Study Context box first!"
    try:
        resp = ai_call([{"role":"system","content":"Reformat messy notes into a clean structured outline: bold title, ## headers, bullet points, 2-sentence summary at bottom."},
                        {"role":"user","content":f"Clean up:\n\n{notes_text}"}], max_tokens=800, temperature=0.4)
        return resp.choices[0].message.content.strip()
    except Exception as e: return f"Error: {str(e)}"

def get_citations(history):
    if len(history) < 2: return "Have a conversation first!"
    convo = "\n".join([f"NOVA: {get_text(m.get('content',''))}" for m in history if m.get("role") == "assistant"])
    try:
        resp = ai_call([{"role":"system","content":"Extract 3 factual claims and give a search URL for each.\nFormat:\n**Claim:** [claim]\n**Search:** [URL]\nRepeat for 3 claims."},
                        {"role":"user","content":f"Find sources:\n\n{convo[:2000]}"}], max_tokens=500, temperature=0.3)
        return "## Source Verification\n\n" + resp.choices[0].message.content.strip()
    except Exception as e: return f"Error: {str(e)}"

def export_pdf(history):
    if len(history) < 2: return None, "Have a conversation first!"
    try:
        from fpdf import FPDF
        import tempfile
        convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
        resp = ai_call([{"role":"system","content":"Convert this tutoring session into a clean study guide: Title, Key Concepts, Step-by-Step Solutions, Summary. Plain text only."},
                        {"role":"user","content":f"Study guide:\n\n{convo[:4000]}"}], max_tokens=1200, temperature=0.4)
        guide_text = resp.choices[0].message.content.strip()
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "Nova AI - Study Guide", ln=True, align="C")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, "nova-ai-public.onrender.com", ln=True, align="C")
        pdf.ln(6)
        pdf.set_font("Helvetica", "", 11)
        for line in guide_text.split("\n"):
            line = line.strip()
            if not line: pdf.ln(3); continue
            pdf.multi_cell(0, 6, line.encode("latin-1", "replace").decode("latin-1"))
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="/tmp/nova_")
        pdf.output(tmp.name)
        return tmp.name, "PDF ready!"
    except ImportError: return None, "fpdf2 not installed. Add fpdf2 to requirements.txt"
    except Exception as e: return None, f"PDF Error: {str(e)}"

def update_streak(streak_data):
    today = str(datetime.date.today())
    data = dict(streak_data)
    if data.get("last_date") != today:
        yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
        data["streak"] = data.get("streak", 0) + 1 if data.get("last_date") == yesterday else 1
        data["problems_today"] = 0
        data["last_date"] = today
    data["problems_today"] = data.get("problems_today", 0) + 1
    goal = data.get("daily_goal", 3)
    pct = min(100, int((data["problems_today"] / goal) * 100))
    badges = data.get("badges", [])
    popup_html = ""
    badge_icon = ""
    if data["problems_today"] >= goal and "daily_goal" not in badges:
        badges.append("daily_goal"); badge_icon = "🏆"
        popup_html = f"<div class='badge-popup show'>🏆 Daily Goal Hit!<br><small>You solved {goal} problems today!</small></div><script>setTimeout(()=>{{var b=document.querySelector('.badge-popup');if(b)b.classList.remove('show')}},4000)</script>"
    if data["streak"] >= 7 and "streak_7" not in badges:
        badges.append("streak_7"); badge_icon = "⭐"
        popup_html = "<div class='badge-popup show'>⭐ 7-Day Streak!<br><small>A full week!</small></div><script>setTimeout(()=>{{var b=document.querySelector('.badge-popup');if(b)b.classList.remove('show')}},4000)</script>"
    elif data["streak"] >= 3 and "streak_3" not in badges:
        badges.append("streak_3"); badge_icon = "🔥"
        popup_html = "<div class='badge-popup show'>🔥 3-Day Streak!<br><small>You're on fire!</small></div><script>setTimeout(()=>{{var b=document.querySelector('.badge-popup');if(b)b.classList.remove('show')}},4000)</script>"
    data["badges"] = badges
    html = (f"<div class='streak-bar'>"
            f"<div class='streak-item'>🔥 <span class='streak-num'>{data['streak']}</span> day streak</div>"
            f"<div class='streak-item'>Today: <div class='goal-bar-bg'><div class='goal-bar-fill' style='width:{pct}%'></div></div> {data['problems_today']}/{goal}</div>"
            f"<div class='streak-item'>{badge_icon}</div></div>{popup_html}")
    return data, html

def generate_exit_ticket(history):
    if len(history) < 2: return ""
    convo = "\n".join([f"{m['role'].upper()}: {get_text(m.get('content',''))}" for m in history if m.get("role") in ("user","assistant")])
    try:
        resp = ai_call([{"role":"system","content":"Generate a 3-bullet exit ticket.\nFormat:\n## Session Exit Ticket\n\n**What we covered:**\n- [concept 1]\n- [concept 2]\n- [concept 3]\n\n**Remember:** [one key sentence]"},
                        {"role":"user","content":f"Summarize:\n\n{convo[:3000]}"}], max_tokens=300, temperature=0.4)
        return resp.choices[0].message.content.strip()
    except Exception as e: return f"Error: {str(e)}"


def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=f"{RENDER_URL}/?success=true",
            cancel_url=f"{RENDER_URL}/?canceled=true",
        )
        return session.url
    except Exception as e:
        return f"Error: {str(e)}"


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks() as demo:

    gr.HTML("<div id='title-area'><h1>NOVA <span>AI</span></h1><p>Version 5.0 &nbsp;•&nbsp; Smart Tutor</p></div>")

    streak_display = gr.HTML(
        "<div class='streak-bar'>"
        "<div class='streak-item'>🔥 <span class='streak-num'>0</span> day streak</div>"
        "<div class='streak-item'>Today: <div class='goal-bar-bg'><div class='goal-bar-fill' style='width:0%'></div></div> 0/3</div>"
        "</div>"
    )

    plus_banner = gr.HTML("""<div class='plus-banner'>
        <div class='plus-banner-text'>🌟 <strong>Nova Plus</strong> — image upload, PDF export &amp; unlimited Quiz Mode</div>
        <div class='plus-banner-actions'>
            <input class='banner-input' id='banner-code-input' type='password' placeholder='Enter Plus code...' />
            <button class='banner-activate-btn' onclick='(function(){var code=document.getElementById("banner-code-input").value;var tb=document.querySelector("#plus-code-box textarea");if(tb){tb.value=code;tb.dispatchEvent(new Event("input",{bubbles:true}));}setTimeout(function(){document.getElementById("plus-activate-trigger").click();},100);})()'>Activate</button>
            <button class='banner-getplus-btn' id='stripe-banner-btn' onclick='(function(){document.getElementById("stripe-banner-btn").innerText="Loading...";fetch("/stripe_url").then(r=>r.json()).then(d=>{if(d.url){window.open(d.url,"_blank");}document.getElementById("stripe-banner-btn").innerText="Get Plus $4/mo";}).catch(()=>{window.open("https://ko-fi.com/guranshb","_blank");document.getElementById("stripe-banner-btn").innerText="Get Plus $4/mo";})})()'>Get Plus $4/mo →</button>
        </div>
    </div>""")

    gr.HTML("""
    <div class='nova-modal-overlay' id='nova-plus-modal'>
      <div class='nova-modal'>
        <button class='close-btn' onclick="document.getElementById('nova-plus-modal').classList.remove('active')">x</button>
        <div style='font-size:2.2em;margin-bottom:10px;'>🌟</div>
        <h2>Upgrade to Nova Plus</h2>
        <p class='subtitle'>This feature requires Nova Plus</p>
        <div class='features'>
          <div>✅ Unlimited messages</div>
          <div>✅ Image and worksheet upload</div>
          <div>✅ Quiz Mode</div>
          <div>✅ PDF study guide export</div>
          <div>✅ Priority AI responses</div>
        </div>
        <p class='price'>Only <span class='amount'>$4</span><span style='color:#4a6fa5;font-size:0.7em;'>/month</span></p>
        <button class='kofi-btn' id='stripe-modal-btn' onclick='(function(){document.getElementById("stripe-modal-btn").innerText="Loading...";fetch("/stripe_url").then(r=>r.json()).then(d=>{if(d.url){window.open(d.url,"_blank");}document.getElementById("stripe-modal-btn").innerText="Get Nova Plus";}).catch(()=>{window.open("https://ko-fi.com/guranshb","_blank");document.getElementById("stripe-modal-btn").innerText="Get Nova Plus";})})()'>Get Nova Plus — $4/month</button>
        <p style='color:#4a6fa5;font-size:0.78em;'>After paying you will receive a code within 24 hours.</p>
        <div class='code-section'>
          <p>Already have a code?</p>
          <div class='code-row'>
            <input type='password' id='modal-code-input' placeholder='NOVA-PLUS-XXXXX' />
            <button onclick='(function(){var code=document.getElementById("modal-code-input").value;var tb=document.querySelector("#plus-code-box textarea");if(tb){tb.value=code;tb.dispatchEvent(new Event("input",{bubbles:true}));}setTimeout(function(){document.getElementById("plus-activate-trigger").click();document.getElementById("nova-plus-modal").classList.remove("active");},100);})()'>Activate</button>
          </div>
        </div>
      </div>
    </div>
    <script>
      function showPlusModal(){document.getElementById("nova-plus-modal").classList.add("active");}
      document.getElementById("nova-plus-modal").addEventListener("click",function(e){if(e.target===this)this.classList.remove("active");});
    </script>
    """)

    chat_store     = gr.State(load_chats())
    active_chat_id = gr.State(None)
    last_msg_state = gr.State({})
    plus_state     = gr.State(False)
    streak_state   = gr.State({"streak":0,"problems_today":0,"daily_goal":3,"last_date":"","badges":[]})

    with gr.Row():

        with gr.Column(scale=1, elem_classes="history-sidebar"):
            gr.HTML("<div class='section-label'>Chats</div>")
            new_chat_btn  = gr.Button("+ New Chat",  variant="secondary", size="sm")
            save_chat_btn = gr.Button("Save Chat", variant="secondary", size="sm")
            chat_list_html = gr.HTML("<p style='color:#4a6fa5;font-size:0.8em;'>No saved chats yet.</p>")
            load_chat_id  = gr.Textbox(visible=False, elem_id="load_chat_id_box")
            load_chat_btn = gr.Button(visible=False,  elem_id="load_chat_trigger")

        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                value=[intro_msg], height=430,
                elem_classes="chatbot-container", show_label=False,
                latex_delimiters=[{"left":"$$","right":"$$","display":True},{"left":"$","right":"$","display":False}]
            )
            with gr.Row(elem_id="input-row"):
                msg = gr.MultimodalTextbox(show_label=False, placeholder="Ask Nova anything, or upload a photo...", scale=10, elem_id="query-box", file_types=[".pdf","image"])
                submit_btn = gr.Button("Send", variant="primary", scale=1)
            with gr.Row(elem_id="tools-row"):
                flashcard_btn = gr.Button("Flashcards",   variant="secondary", size="sm")
                quiz_btn      = gr.Button("Quiz Me",      variant="secondary", size="sm")
                citation_btn  = gr.Button("Citations",    variant="secondary", size="sm")
                pdf_btn       = gr.Button("Export PDF",   variant="secondary", size="sm")
            tool_output  = gr.Markdown(visible=False)
            pdf_download = gr.File(visible=False, label="Download Study Guide PDF")

        with gr.Column(scale=1, elem_classes="settings-sidebar"):
            gr.HTML("<div class='section-label'>Settings</div>")
            subject = gr.Dropdown(["General","Math","Science","History"], label="Subject", value="General")
            mode = gr.Radio(["Normal","Tutor Mode","Quiz Mode","Crunch Time"], label="Mode", value="Normal")
            notes = gr.Textbox(label="Study Notes", lines=5, placeholder="Paste your notes here...")
            cleanup_btn = gr.Button("Clean Up Notes", variant="secondary", size="sm")
            gr.HTML("<div class='section-label' style='margin-top:16px;'>Nova Plus</div>")
            plus_code_input = gr.Textbox(show_label=False, placeholder="Enter Plus code...", type="password", elem_id="plus-code-box")
            plus_activate_btn = gr.Button("Activate", variant="primary", size="sm", elem_id="plus-activate-trigger")
            plus_status = gr.Markdown("<p style='color:#4a6fa5;font-size:0.78em;'>Free: 20 messages/session</p>")

    # ── Handlers ──────────────────────────────────────────────────────────────

    def activate_plus(code, history):
        if is_plus(code):
            return True, "✅ **Nova Plus active!** All features unlocked.", gr.update(visible=False)
        return False, "❌ Invalid code. Get Nova Plus at [ko-fi.com/guranshb](https://ko-fi.com/guranshb).", gr.update(visible=True)

    def user_fn(message, history, plus):
        user_text = message.get("text","") if isinstance(message, dict) else str(message)
        files     = message.get("files",[]) if isinstance(message, dict) else []
        if not user_text.strip() and not files:
            return gr.update(value=None), history, {}
        if not plus and count_user_messages(history) >= MSG_LIMIT_FREE:
            history = history + [{"role":"assistant","content":f"You have reached the {MSG_LIMIT_FREE} message limit. Upgrade to Nova Plus for unlimited messages!"}]
            return gr.update(value=None), history, {}
        if files and not plus:
            history = history + [{"role":"assistant","content":"Image upload is a Nova Plus feature. Get Nova Plus to unlock it!"}]
            return gr.update(value=None), history, {}
        display = user_text if user_text.strip() else "Image uploaded"
        history  = history + [{"role":"user","content":display}]
        return gr.update(value=None, interactive=False), history, {"text": user_text, "files": files}

    def bot_fn(last_msg, history, subject, mode, notes, streak_data):
        user_message = ""
        for m in reversed(history):
            if m.get("role") == "user":
                user_message = get_text(m.get("content","")).strip()
                if user_message == "Image uploaded": user_message = ""
                break
        image_paths = []
        if isinstance(last_msg, dict):
            for f in last_msg.get("files",[]):
                path = f.get("path", f) if isinstance(f, dict) else f
                if path: image_paths.append(path)
        if not user_message and not image_paths:
            yield history; return
        thinking_block = None
        answer_text = ""
        history = list(history)
        for thought, answer in respond(user_message, image_paths, history[:-1], subject, mode, notes):
            if thought is not None:
                thinking_block = thought
                yield history + [thinking_block]
            if answer:
                answer_text = answer
                yield history + ([thinking_block] if thinking_block else []) + [{"role":"assistant","content":answer_text}]

    def bot_fn_streak(last_msg, history, subject, mode, notes, streak_data):
        final_history = history
        for h in bot_fn(last_msg, history, subject, mode, notes, streak_data):
            final_history = h
            yield h, streak_data, gr.update()
        new_streak, streak_html = update_streak(streak_data)
        yield final_history, new_streak, gr.update(value=streak_html)

    def save_chat_fn(history, chats, active_id):
        if len(history) <= 1: return chats, active_id, gr.update(), gr.update()
        cid = active_id if active_id else str(uuid.uuid4())[:8]
        chats = dict(chats)
        chats[cid] = {"title": chat_title(history), "history": history, "ts": time.time()}
        save_chats(chats)
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
        if not cid or cid not in chats: return gr.update(), gr.update(), gr.update()
        return chats[cid]["history"], cid, gr.update(value=get_chat_list_html(chats, cid))

    def quiz_fn_gated(history, plus):
        if not plus: return gr.update(value="<script>showPlusModal()</script>Quiz Mode is Nova Plus only.", visible=True)
        return gr.update(value=generate_quiz(history), visible=True)

    def pdf_fn_gated(history, plus):
        if not plus: return gr.update(visible=False), gr.update(value="<script>showPlusModal()</script>PDF Export is Nova Plus only.", visible=True)
        path, msg_txt = export_pdf(history)
        if path: return gr.update(value=path, visible=True), gr.update(value=msg_txt, visible=True)
        return gr.update(visible=False), gr.update(value=msg_txt, visible=True)

    def cleanup_fn(notes_text):
        result = cleanup_notes(notes_text)
        return result, gr.update(value=result, visible=True)

    # Wire
    plus_activate_btn.click(activate_plus, [plus_code_input, chatbot], [plus_state, plus_status, plus_banner])

    submit_btn.click(
        user_fn, [msg, chatbot, plus_state], [msg, chatbot, last_msg_state]
    ).then(
        bot_fn_streak, [last_msg_state, chatbot, subject, mode, notes, streak_state], [chatbot, streak_state, streak_display]
    ).then(lambda: gr.update(interactive=True), None, [msg])

    msg.submit(
        user_fn, [msg, chatbot, plus_state], [msg, chatbot, last_msg_state]
    ).then(
        bot_fn_streak, [last_msg_state, chatbot, subject, mode, notes, streak_state], [chatbot, streak_state, streak_display]
    ).then(lambda: gr.update(interactive=True), None, [msg])

    save_chat_btn.click(save_chat_fn, [chatbot, chat_store, active_chat_id], [chat_store, active_chat_id, chat_list_html, tool_output])
    new_chat_btn.click(new_chat_fn,   [chatbot, chat_store, active_chat_id], [chatbot, chat_store, active_chat_id, chat_list_html])
    load_chat_btn.click(load_chat_fn, [load_chat_id, chat_store],            [chatbot, active_chat_id, chat_list_html])

    flashcard_btn.click(lambda h: gr.update(value=generate_flashcards(h), visible=True), [chatbot], [tool_output])
    quiz_btn.click(quiz_fn_gated,     [chatbot, plus_state], [tool_output])
    citation_btn.click(lambda h: gr.update(value=get_citations(h), visible=True), [chatbot], [tool_output])
    pdf_btn.click(pdf_fn_gated,       [chatbot, plus_state], [pdf_download, tool_output])
    cleanup_btn.click(cleanup_fn,     [notes], [notes, tool_output])

# Mount Stripe checkout route
try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn

    app_fastapi = FastAPI()

    @app_fastapi.get("/stripe_url")
    def stripe_url_route():
        url = create_checkout_session()
        if url.startswith("Error"):
            return JSONResponse({"url": None, "error": url})
        return JSONResponse({"url": url})

    import gradio as gr
    demo_app = gr.mount_gradio_app(app_fastapi, demo, path="/")
    uvicorn.run(demo_app, host="0.0.0.0", port=7860)
except Exception:
    # Fallback to normal launch if FastAPI not available
    demo.launch(css=custom_css)
