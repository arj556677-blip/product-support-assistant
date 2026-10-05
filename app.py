import os, base64, uuid, requests
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from openai import OpenAI

import database as db
import rag_engine as rag
import support_assistant as sa
import evaluator as ev

load_dotenv()

# Initialize DB & RAG Knowledge Base on app startup
db.init_db()
rag.load_and_index_knowledge_base()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AOAI_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
TEXT_MODEL = os.getenv("TEXT_MODEL_DEPLOYMENT", "gpt-4.1-mini")
VISION_MODEL = os.getenv("VISION_MODEL_DEPLOYMENT") or TEXT_MODEL
IMAGE_MODEL = os.getenv("IMAGE_MODEL_DEPLOYMENT", "")
SPEECH_ENDPOINT = os.getenv("SPEECH_ENDPOINT", "").rstrip("/")
SPEECH_KEY = os.getenv("SPEECH_API_KEY", "")
SPEECH_REGION = os.getenv("SPEECH_REGION", "eastus")
CONTENT_ENDPOINT = os.getenv("CONTENT_ENDPOINT", "").rstrip("/")
CONTENT_KEY = os.getenv("CONTENT_API_KEY", "")
CONTENT_API_VERSION = os.getenv("CONTENT_API_VERSION", "2025-11-01")

def client():
    if not AOAI_ENDPOINT or not AOAI_KEY:
        raise RuntimeError("Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env")
    endpoint = AOAI_ENDPOINT.removesuffix("/openai/v1").rstrip("/")
    return OpenAI(api_key=AOAI_KEY, base_url=f"{endpoint}/openai/v1/")

def image_client():
    if not CONTENT_ENDPOINT or not CONTENT_KEY:
        raise RuntimeError("Set CONTENT_ENDPOINT and CONTENT_API_KEY in .env")
    endpoint = CONTENT_ENDPOINT.removesuffix("/openai/v1").removesuffix("/openai").rstrip("/")
    return OpenAI(
        api_key=CONTENT_KEY,
        base_url=f"{endpoint}/openai/v1/",
        default_query={"api-version": "preview"},
    )

def text_response(prompt, system="You are a helpful AI assistant."):
    r = client().responses.create(model=TEXT_MODEL, instructions=system, input=prompt)
    return r.output_text

# ===== PRIMARY AI PRODUCT SUPPORT ASSISTANT ROUTES =====

@app.get("/")
def home():
    """Renders the main AI Product Support Assistant Dashboard UI."""
    return render_template("index.html")

@app.post("/api/chat")
def api_chat():
    """Main AI Support Chat Endpoint with RAG + SQLite Warranty Routing."""
    try:
        data = request.json or {}
        msg = data.get("message", "").strip()
        session_id = data.get("session_id", "default_user_session")
        
        if not msg:
            return jsonify(error="Enter a question or serial number."), 400

        result = sa.process_support_query(msg, session_id=session_id)
        return jsonify(result)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.post("/api/warranty/check")
def api_warranty_check():
    """Direct SQLite Warranty & Serial Number Verification Endpoint."""
    try:
        data = request.json or {}
        sn = data.get("serial_number", "").strip()
        if not sn:
            return jsonify(error="Please provide a valid product serial number."), 400
        
        result = db.check_warranty(sn)
        return jsonify(result)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.get("/api/warranties")
def api_warranties_list():
    """Returns sample products and warranty database records for UI testing."""
    try:
        warranties = db.get_all_warranties()
        products = db.get_all_products()
        return jsonify(warranties=warranties, products=products)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.get("/api/knowledge")
def api_knowledge_list():
    """Returns list of indexed knowledge chunks and source documents."""
    try:
        chunks = rag.get_indexed_chunks()
        return jsonify(chunks=chunks, total_chunks=len(chunks))
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.post("/api/evaluate")
def api_evaluate():
    """Executes automated 35-query evaluation benchmark suite and returns metrics."""
    try:
        report = ev.run_evaluation_benchmark()
        return jsonify(report)
    except Exception as e:
        return jsonify(error=str(e)), 500

# ===== LEGACY & UTILITY LAB ROUTES =====

@app.get("/chat")
def legacy_chat(): 
    return render_template("index.html")

@app.get("/text-analysis")
def text_analysis(): 
    return render_template("text_analysis.html")

@app.post("/api/text-analysis")
def api_text_analysis():
    try:
        text = (request.json or {}).get("text", "").strip()
        if not text: return jsonify(error="Enter text."), 400
        prompt = f"""Analyze the following text and return exactly these sections:
1. Sentiment
2. Keywords
3. Entities (organization, person, location, date, product where applicable)
4. Summary

TEXT:
{text}"""
        return jsonify(result=text_response(prompt))
    except Exception as e: return jsonify(error=str(e)), 500

@app.get("/vision")
def vision(): return render_template("vision.html")

@app.post("/api/vision")
def api_vision():
    try:
        f = request.files.get("image")
        prompt = request.form.get("prompt", "Describe this image in detail.").strip()
        if not f: return jsonify(error="Upload an image."), 400
        data = base64.b64encode(f.read()).decode()
        mime = f.mimetype or "image/jpeg"
        r = client().responses.create(
            model=VISION_MODEL,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"data:{mime};base64,{data}"}
            ]}]
        )
        return jsonify(result=r.output_text)
    except Exception as e: return jsonify(error=str(e)), 500

@app.post("/api/enquire")
def api_enquire():
    """Allows users to chat & enquire via text or voice about an inspection or analysis result."""
    try:
        data = request.json or {}
        context = data.get("context", "").strip()
        question = data.get("question", "").strip()
        history = data.get("history", [])

        if not question or not context:
            return jsonify(error="Analysis context and question are required."), 400

        system_msg = (
            "You are an expert AI Hardware Inspection & Technical Support Assistant. "
            "The user is asking follow-up questions regarding the following inspection analysis result:\n\n"
            f"--- ANALYSIS RESULT ---\n{context}\n-----------------------\n\n"
            "Answer the user's questions clearly, accurately, and concisely based on the analysis context above. "
            "Provide helpful hardware advice, device descriptions, port identification, or troubleshooting steps."
        )

        messages = [{"role": "system", "content": system_msg}]
        for item in history[-6:]:
            if isinstance(item, dict) and item.get("role") and item.get("content"):
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": question})

        cli = client()
        try:
            r = cli.chat.completions.create(
                model=TEXT_MODEL,
                messages=messages
            )
            answer = r.choices[0].message.content
        except Exception:
            full_prompt = f"{system_msg}\n\nUser Question: {question}"
            r = cli.responses.create(model=TEXT_MODEL, input=full_prompt)
            answer = getattr(r, "output_text", str(r))

        return jsonify(answer=answer)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.get("/speech")
def speech(): 
    return render_template("index.html")

@app.post("/api/speech")
def api_speech():
    try:
        f = request.files.get("audio")
        if not f: return jsonify(error="Upload an audio file."), 400
        if not SPEECH_KEY: raise RuntimeError("Set SPEECH_API_KEY.")
        language = request.form.get("language", "en-US")
        url = f"{SPEECH_ENDPOINT}/speechtotext/v3.2/transcriptions:transcribe?api-version=2024-11-15"
        headers = {"Ocp-Apim-Subscription-Key": SPEECH_KEY}
        files = {"audio": (f.filename, f.stream, f.mimetype or "audio/wav")}
        data = {"definition": '{"locales":["' + language + '"],"profanityFilterMode":"Masked"}'}
        r = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        if not r.ok:
            return jsonify(error=f"Speech service returned {r.status_code}: {r.text}"), r.status_code
        return jsonify(result=r.json())
    except Exception as e: return jsonify(error=str(e)), 500

@app.get("/content-understanding")
def content_understanding(): return render_template("content.html")

@app.post("/api/content-understanding")
def api_content():
    try:
        f = request.files.get("file")
        analyzer = request.form.get("analyzer", "prebuilt-documentSearch")
        if not f: return jsonify(error="Upload a file."), 400
        if not CONTENT_ENDPOINT or not CONTENT_KEY:
            raise RuntimeError("Set CONTENT_ENDPOINT and CONTENT_API_KEY.")
        url = f"{CONTENT_ENDPOINT}/contentunderstanding/analyzers/{analyzer}:analyze?api-version={CONTENT_API_VERSION}"
        headers = {"Ocp-Apim-Subscription-Key": CONTENT_KEY}
        r = requests.post(url, headers=headers, files={"file": (f.filename, f.stream, f.mimetype)}, timeout=180)
        if not r.ok:
            return jsonify(error=f"Content Understanding returned {r.status_code}: {r.text}"), r.status_code
        return jsonify(result=r.json())
    except Exception as e: return jsonify(error=str(e)), 500

@app.get("/uploads/<name>")
def uploads(name): return send_file(os.path.join("uploads", name))

@app.get("/health")
def health():
    return jsonify(
        status="ok",
        database="connected",
        rag_chunks=len(rag.get_indexed_chunks()),
        azure_openai_endpoint=bool(AOAI_ENDPOINT),
        text_model=TEXT_MODEL,
        vision_model=VISION_MODEL,
        speech=bool(SPEECH_KEY),
        content_understanding=bool(CONTENT_KEY)
    )

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=False
    )

