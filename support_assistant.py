import os
import re
from openai import OpenAI
import database as db
import rag_engine as rag

# Global session store for conversation history: session_id -> list of message dicts
SESSION_STORE = {}

def get_openai_client():
    """Builds Azure OpenAI client using .env configuration."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    
    if not endpoint or not api_key:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be configured in .env")
        
    base_endpoint = endpoint.removesuffix("/openai/v1").rstrip("/")
    return OpenAI(api_key=api_key, base_url=f"{base_endpoint}/openai/v1/")

def extract_serial_number(user_message):
    """Detects serial numbers like SN1001 or serial number queries."""
    sn_match = re.search(r'\b(SN\d{4,6})\b', user_message, re.IGNORECASE)
    if sn_match:
        return sn_match.group(1).upper()
    return None

def is_out_of_domain(user_message):
    """Detects obvious non-product/unsupported queries."""
    msg = user_message.lower()
    unsupported_keywords = [
        "football", "cricket", "match", "weather", "recipe", "bake", "cake",
        "election", "president", "movie", "song", "joke", "crypto", "bitcoin"
    ]
    return any(kw in msg for kw in unsupported_keywords)

def process_support_query(user_message, session_id="default_session"):
    """
    Main application workflow for handling product support questions:
    1. Check for Out-Of-Domain intent -> Trigger Fallback
    2. Check for Warranty / Serial Number lookup -> SQLite Query + LLM Explanation
    3. Perform RAG Knowledge Base Search -> Grounded LLM Response with Citations
    4. Low confidence / missing context -> Grounded Fallback Message
    """
    if not user_message or not user_message.strip():
        return {
            "answer": "Please enter a question or serial number.",
            "sources": [],
            "intent": "empty_input",
            "grounded": True
        }

    user_msg_clean = user_message.strip()

    # Manage session history
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []
    
    chat_history = SESSION_STORE[session_id]

    # --- ROUTE 1: OUT OF DOMAIN FALLBACK ---
    if is_out_of_domain(user_msg_clean):
        fallback_reply = (
            "I am the TechPro AI Product Support Assistant. I am specialized in answering questions "
            "about TechPro hardware products, troubleshooting, specs, warranty policies, and serial lookups. "
            "I don't have information regarding general trivia or external topics. "
            "Please ask a product-support question or provide a product serial number!"
        )
        chat_history.append({"role": "user", "content": user_msg_clean})
        chat_history.append({"role": "assistant", "content": fallback_reply})
        return {
            "answer": fallback_reply,
            "sources": [],
            "intent": "out_of_domain",
            "grounded": True,
            "fallback_triggered": True
        }

    # --- ROUTE 2: WARRANTY / SERIAL NUMBER LOOKUP ---
    extracted_sn = extract_serial_number(user_msg_clean)
    is_warranty_query = "warranty" in user_msg_clean.lower() or "serial" in user_msg_clean.lower() or extracted_sn is not None

    if is_warranty_query and extracted_sn:
        warranty_info = db.check_warranty(extracted_sn)
        
        if warranty_info["found"]:
            system_prompt = (
                "You are an official TechPro Product Support Representative. "
                "Synthesize the following authoritative database warranty verification result into a clear, polite response. "
                "Mention the Product Name, Serial Number, Purchase Date, Expiry Date, Warranty Status (Active or Expired), and remaining days. "
                "Do NOT invent or modify dates or status."
            )
            user_prompt = f"Serial Verification Result from SQLite DB:\n{warranty_info}"
            
            try:
                model_name = os.getenv("TEXT_MODEL_DEPLOYMENT", "gpt-4.1-mini")
                client = get_openai_client()
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2
                )
                answer = response.choices[0].message.content
            except Exception as e:
                # Fallback to direct structured text if model call fails
                answer = (
                    f"**Warranty Status for {warranty_info['serial_number']}**\n\n"
                    f"- **Product:** {warranty_info['product_name']}\n"
                    f"- **Customer:** {warranty_info['customer_name']}\n"
                    f"- **Purchase Date:** {warranty_info['purchase_date']}\n"
                    f"- **Warranty Status:** **{warranty_info['status']}** (Expires: {warranty_info['expiry_date']})\n"
                    f"- **Care+ Coverage:** {'Yes' if warranty_info['care_plus'] else 'No'}\n\n"
                    f"{'Your warranty is active and valid.' if warranty_info['is_active'] else 'Your standard warranty coverage has expired. Please contact support for repair options.'}"
                )

            sources = [{"document": "SQLite products.db (warranty_records)", "section": f"Serial Number {extracted_sn}"}]
            
            chat_history.append({"role": "user", "content": user_msg_clean})
            chat_history.append({"role": "assistant", "content": answer})
            
            return {
                "answer": answer,
                "sources": sources,
                "intent": "warranty_lookup",
                "grounded": True,
                "warranty_data": warranty_info
            }
        elif extracted_sn:
            answer = f"⚠️ Serial number **{extracted_sn}** was not found in our official TechPro database. Please verify the serial number printed on your device or box and try again."
            sources = [{"document": "SQLite products.db", "section": "Serial Search"}]
            return {
                "answer": answer,
                "sources": sources,
                "intent": "warranty_lookup",
                "grounded": True,
                "warranty_data": warranty_info
            }

    # --- ROUTE 3: RAG KNOWLEDGE BASE RETRIEVAL ---
    retrieved_chunks = rag.search_knowledge_base(user_msg_clean, top_k=3, min_score=0.08)

    if not retrieved_chunks:
        fallback_reply = (
            "I don't have enough verified information in the TechPro product support knowledge base "
            "to provide a reliable answer to this question.\n\n"
            "**Recommended Next Step:** Please contact a live support representative at **support@techpro-electronics.com** "
            "or call our support hotline at **+1 (800) 555-TECH** for assistance."
        )
        chat_history.append({"role": "user", "content": user_msg_clean})
        chat_history.append({"role": "assistant", "content": fallback_reply})
        
        return {
            "answer": fallback_reply,
            "sources": [],
            "intent": "rag_knowledge",
            "grounded": True,
            "fallback_triggered": True
        }

    # Construct Grounded Prompt with retrieved context
    context_str = "\n\n---\n\n".join([
        f"[SOURCE: {c['source']} | SECTION: {c['section']}]\n{c['text']}"
        for c in retrieved_chunks
    ])

    system_grounding_prompt = (
        "You are an expert AI Product Support Assistant for TechPro Consumer Electronics.\n\n"
        "STRICT GROUNDING RULES:\n"
        "1. Answer the user's question USING ONLY the supplied product-support context below.\n"
        "2. Do NOT invent or extrapolate product specifications, troubleshooting steps, warranty terms, or company policies.\n"
        "3. If the supplied context does NOT contain sufficient information to answer accurately, explicitly state that you do not have enough verified information and recommend contacting support.\n"
        "4. Include explicit source references in your response citing the source file name and section title.\n"
        "5. Keep your tone professional, empathetic, and clear.\n\n"
        f"SUPPLIED PRODUCT SUPPORT CONTEXT:\n{context_str}"
    )

    # Format recent history (last 4 turns)
    recent_history = chat_history[-4:] if chat_history else []
    messages = [{"role": "system", "content": system_grounding_prompt}]
    for h in recent_history:
        messages.append(h)
    messages.append({"role": "user", "content": user_msg_clean})

    try:
        model_name = os.getenv("TEXT_MODEL_DEPLOYMENT", "gpt-4.1-mini")
        client = get_openai_client()
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.3
        )
        answer = response.choices[0].message.content
    except Exception as e:
        # Fallback formatting if LLM endpoint encounters error
        answer = f"**Retrieved Product Knowledge ({retrieved_chunks[0]['section']}):**\n\n{retrieved_chunks[0]['text']}\n\n*(Source: {retrieved_chunks[0]['source']})*"

    sources = [{"document": c["source"], "section": c["section"], "relevance_score": c["score"]} for c in retrieved_chunks]

    chat_history.append({"role": "user", "content": user_msg_clean})
    chat_history.append({"role": "assistant", "content": answer})

    return {
        "answer": answer,
        "sources": sources,
        "intent": "rag_knowledge",
        "grounded": True
    }

def clear_session(session_id):
    if session_id in SESSION_STORE:
        del SESSION_STORE[session_id]
