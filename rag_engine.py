import os
import re
import math
from collections import Counter

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")

# Simple English stop words set for keyword filtering
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've",
    "your", "yours", "yourself", "yourselves"
}

_chunks_cache = []
_idf_weights = {}

def tokenize(text):
    """Clean and tokenize text into keywords."""
    words = re.findall(r'\w+', text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]

def split_document_into_chunks(filepath):
    """Splits a document file into logical section chunks."""
    filename = os.path.basename(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by section headers (## header) or double newlines
    lines = content.splitlines()
    chunks = []
    current_header = filename
    current_lines = []
    chunk_counter = 1

    for line in lines:
        if line.startswith("# ") or line.startswith("## "):
            if current_lines:
                chunk_text = "\n".join(current_lines).strip()
                if len(chunk_text) > 30:
                    chunks.append({
                        "id": f"{filename}_chunk_{chunk_counter}",
                        "source": filename,
                        "section": current_header,
                        "text": chunk_text
                    })
                    chunk_counter += 1
                current_lines = []
            current_header = line.strip("# ").strip()
        current_lines.append(line)

    if current_lines:
        chunk_text = "\n".join(current_lines).strip()
        if len(chunk_text) > 30:
            chunks.append({
                "id": f"{filename}_chunk_{chunk_counter}",
                "source": filename,
                "section": current_header,
                "text": chunk_text
            })

    return chunks

def load_and_index_knowledge_base():
    """Indexes all files in the knowledge directory using TF-IDF."""
    global _chunks_cache, _idf_weights
    _chunks_cache = []
    
    if not os.path.exists(KNOWLEDGE_DIR):
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        return

    for root, _, files in os.walk(KNOWLEDGE_DIR):
        for file in files:
            if file.endswith(".txt") or file.endswith(".md"):
                full_path = os.path.join(root, file)
                doc_chunks = split_document_into_chunks(full_path)
                for c in doc_chunks:
                    c["tokens"] = tokenize(c["text"])
                    c["tf"] = Counter(c["tokens"])
                    _chunks_cache.append(c)

    # Compute IDF weights across all chunks
    total_docs = len(_chunks_cache)
    if total_docs == 0:
        return

    doc_freq = Counter()
    for c in _chunks_cache:
        unique_words = set(c["tokens"])
        for w in unique_words:
            doc_freq[w] += 1

    _idf_weights = {
        w: math.log((total_docs + 1) / (df + 1)) + 1
        for w, df in doc_freq.items()
    }

def cosine_similarity(query_tokens, chunk):
    """Calculates TF-IDF cosine similarity score between query and chunk."""
    if not query_tokens or not chunk["tokens"]:
        return 0.0

    q_tf = Counter(query_tokens)
    c_tf = chunk["tf"]

    all_words = set(q_tf.keys()).union(set(c_tf.keys()))
    
    dot_product = 0.0
    q_norm_sq = 0.0
    c_norm_sq = 0.0

    for w in all_words:
        idf = _idf_weights.get(w, 1.0)
        q_val = q_tf.get(w, 0) * idf
        c_val = c_tf.get(w, 0) * idf

        dot_product += q_val * c_val
        q_norm_sq += q_val ** 2
        c_norm_sq += c_val ** 2

    if q_norm_sq == 0 or c_norm_sq == 0:
        return 0.0

    score = dot_product / (math.sqrt(q_norm_sq) * math.sqrt(c_norm_sq))

    # Bonus score boost if exact phrase or serial number matches
    query_raw = " ".join(query_tokens).lower()
    if query_raw in chunk["text"].lower():
        score += 0.15

    return min(score, 1.0)

def search_knowledge_base(query, top_k=3, min_score=0.08):
    """
    Searches the knowledge base for top matching chunks given a query.
    Returns list of dicts: [{source, section, text, score, id}, ...]
    """
    if not _chunks_cache:
        load_and_index_knowledge_base()

    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    scored_results = []
    for chunk in _chunks_cache:
        score = cosine_similarity(q_tokens, chunk)
        if score >= min_score:
            scored_results.append({
                "id": chunk["id"],
                "source": chunk["source"],
                "section": chunk["section"],
                "text": chunk["text"],
                "score": round(score, 4)
            })

    # Sort descending by relevance score
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    return scored_results[:top_k]

def get_indexed_chunks():
    if not _chunks_cache:
        load_and_index_knowledge_base()
    return [{
        "id": c["id"],
        "source": c["source"],
        "section": c["section"],
        "text_preview": c["text"][:160] + "..." if len(c["text"]) > 160 else c["text"]
    } for c in _chunks_cache]

if __name__ == "__main__":
    load_and_index_knowledge_base()
    print(f"Indexed {len(_chunks_cache)} chunks.")
    res = search_knowledge_base("My laptop is not charging")
    print("Search Result:", res)
