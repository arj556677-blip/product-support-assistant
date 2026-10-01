import time
import support_assistant as sa
import database as db
import rag_engine as rag

# Comprehensive Evaluation Dataset (35 Representative Test Queries)
EVAL_DATASET = [
    # Category 1: Product Specifications & Features (10)
    {"id": 1, "category": "Product Specs", "query": "What processor and RAM does the TechPro Laptop X1 Ultra have?", "expected_type": "rag_knowledge", "key_terms": ["intel", "core", "ultra", "32gb"]},
    {"id": 2, "category": "Product Specs", "query": "What is the battery capacity and charging speed of Laptop X1?", "expected_type": "rag_knowledge", "key_terms": ["75 wh", "100w", "fast charging"]},
    {"id": 3, "category": "Product Specs", "query": "What active noise cancellation rating do the TechPro Earbuds Air Pro have?", "expected_type": "rag_knowledge", "key_terms": ["anc", "45db", "hybrid"]},
    {"id": 4, "category": "Product Specs", "query": "Is the TechPro Smartwatch Ultra 2 suitable for swimming?", "expected_type": "rag_knowledge", "key_terms": ["5 atm", "50 meters", "swimming"]},
    {"id": 5, "category": "Product Specs", "query": "What resolution and refresh rate does the TechPro 7-in-1 USB-C Hub HDMI port support?", "expected_type": "rag_knowledge", "key_terms": ["4k", "60hz"]},
    {"id": 6, "category": "Product Specs", "query": "Does Laptop X1 Ultra have an OLED display?", "expected_type": "rag_knowledge", "key_terms": ["oled", "2.8k", "120hz"]},
    {"id": 7, "category": "Product Specs", "query": "What codecs are supported by the TechPro Earbuds Air Pro?", "expected_type": "rag_knowledge", "key_terms": ["aac", "ldac", "sbc"]},
    {"id": 8, "category": "Product Specs", "query": "What sensors are included in the TechPro Smartwatch Ultra 2?", "expected_type": "rag_knowledge", "key_terms": ["heart rate", "spo2", "ecg"]},
    {"id": 9, "category": "Product Specs", "query": "How heavy is the TechPro Laptop X1 Ultra?", "expected_type": "rag_knowledge", "key_terms": ["1.28 kg", "weight"]},
    {"id": 10, "category": "Product Specs", "query": "Can the 7-in-1 Hub work with macOS and Windows without drivers?", "expected_type": "rag_knowledge", "key_terms": ["plug-and-play", "macos", "windows"]},

    # Category 2: Troubleshooting & Repair (10)
    {"id": 11, "category": "Troubleshooting", "query": "My TechPro Laptop X1 is not charging, what steps should I take?", "expected_type": "rag_knowledge", "key_terms": ["100w", "thunderbolt", "30 seconds", "reset"]},
    {"id": 12, "category": "Troubleshooting", "query": "How do I perform an EC Hard Reset on Laptop X1?", "expected_type": "rag_knowledge", "key_terms": ["power button", "15 seconds", "led"]},
    {"id": 13, "category": "Troubleshooting", "query": "How to fix earbud pairing issues when only one earbud plays sound?", "expected_type": "rag_knowledge", "key_terms": ["charging case", "forget device", "factory reset"]},
    {"id": 14, "category": "Troubleshooting", "query": "My Laptop X1 fan is running constantly and overheating.", "expected_type": "rag_knowledge", "key_terms": ["vents", "task manager", "thermal mode"]},
    {"id": 15, "category": "Troubleshooting", "query": "How do I factory reset my TechPro Earbuds Air Pro?", "expected_type": "rag_knowledge", "key_terms": ["setup button", "10 seconds", "amber"]},
    {"id": 16, "category": "Troubleshooting", "query": "Smartwatch touchscreen is unresponsive, how to force restart?", "expected_type": "rag_knowledge", "key_terms": ["side crown", "action button", "12 seconds"]},
    {"id": 17, "category": "Troubleshooting", "query": "HDMI monitor flickers when connected to 7-in-1 Hub.", "expected_type": "rag_knowledge", "key_terms": ["dp alt mode", "reconnect", "60hz"]},
    {"id": 18, "category": "Troubleshooting", "query": "Smartwatch is not syncing steps to TechPro Fit app.", "expected_type": "rag_knowledge", "key_terms": ["bluetooth", "pull down", "unpair"]},
    {"id": 19, "category": "Troubleshooting", "query": "How do I turn off battery conservation mode on Laptop X1?", "expected_type": "rag_knowledge", "key_terms": ["techpro vantage", "charge threshold"]},
    {"id": 20, "category": "Troubleshooting", "query": "What is the return policy for TechPro hardware purchases?", "expected_type": "rag_knowledge", "key_terms": ["30 days", "money-back", "original packaging"]},

    # Category 3: Warranty & Serial Lookup (5)
    {"id": 21, "category": "Warranty Lookup", "query": "Check warranty for serial number SN1001", "expected_type": "warranty_lookup", "expected_status": "ACTIVE", "expected_sn": "SN1001"},
    {"id": 22, "category": "Warranty Lookup", "query": "Is SN1002 still under warranty?", "expected_type": "warranty_lookup", "expected_status": "EXPIRED", "expected_sn": "SN1002"},
    {"id": 23, "category": "Warranty Lookup", "query": "Verify warranty status for SN1005", "expected_type": "warranty_lookup", "expected_status": "ACTIVE", "expected_sn": "SN1005"},
    {"id": 24, "category": "Warranty Lookup", "query": "Is SN1006 covered?", "expected_type": "warranty_lookup", "expected_status": "EXPIRED", "expected_sn": "SN1006"},
    {"id": 25, "category": "Warranty Lookup", "query": "Check warranty status for invalid serial SN9999", "expected_type": "warranty_lookup", "expected_status": "NOT_FOUND", "expected_sn": "SN9999"},

    # Category 4: Multi-turn / Follow-up queries (5)
    {"id": 26, "category": "Multi-turn", "query": "How long does the battery last on Laptop X1?", "expected_type": "rag_knowledge", "key_terms": ["14 hours", "battery"]},
    {"id": 27, "category": "Multi-turn", "query": "How fast can it charge from 0 to 60%?", "expected_type": "rag_knowledge", "key_terms": ["35 minutes", "100w"]},
    {"id": 28, "category": "Multi-turn", "query": "What is the warranty period for TechPro products?", "expected_type": "rag_knowledge", "key_terms": ["12 month", "1 year"]},
    {"id": 29, "category": "Multi-turn", "query": "What does TechPro Care+ cover?", "expected_type": "rag_knowledge", "key_terms": ["accidental damage", "24 or 36"]},
    {"id": 30, "category": "Multi-turn", "query": "How to contact official TechPro email support?", "expected_type": "rag_knowledge", "key_terms": ["support@techpro-electronics.com", "800"]},

    # Category 5: Out-of-Domain / Unsupported Queries (5)
    {"id": 31, "category": "Out-of-Domain", "query": "Who won yesterday's football match?", "expected_type": "out_of_domain", "key_terms": ["specialized", "support"]},
    {"id": 32, "category": "Out-of-Domain", "query": "Give me a recipe for chocolate cake", "expected_type": "out_of_domain", "key_terms": ["specialized", "support"]},
    {"id": 33, "category": "Out-of-Domain", "query": "Can I repair my motherboard at home with soldering?", "expected_type": "rag_knowledge", "key_terms": ["authorized", "support"]},
    {"id": 34, "category": "Out-of-Domain", "query": "What is the current price of Bitcoin?", "expected_type": "out_of_domain", "key_terms": ["specialized", "support"]},
    {"id": 35, "category": "Out-of-Domain", "query": "Who is the president of France?", "expected_type": "out_of_domain", "key_terms": ["specialized", "support"]}
]

def run_evaluation_benchmark():
    """
    Executes the full evaluation suite and returns metrics dictionary.
    """
    db.init_db()
    rag.load_and_index_knowledge_base()

    results = []
    total_queries = len(EVAL_DATASET)
    total_latency_ms = 0.0
    successful_tasks = 0
    retrieval_relevance_hits = 0
    grounded_count = 0
    warranty_precision_hits = 0

    session_id = "eval_session_benchmark"
    sa.clear_session(session_id)

    for item in EVAL_DATASET:
        q_id = item["id"]
        cat = item["category"]
        query = item["query"]

        start_time = time.time()
        res = sa.process_support_query(query, session_id=session_id)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        total_latency_ms += elapsed_ms

        ans = res.get("answer", "").lower()
        intent = res.get("intent", "")
        sources = res.get("sources", [])
        is_grounded = res.get("grounded", False)

        if is_grounded:
            grounded_count += 1

        # Check retrieval relevance or match quality
        is_success = False
        relevance = 0.0

        if cat == "Warranty Lookup":
            expected_sn = item["expected_sn"]
            expected_st = item["expected_status"]
            w_data = res.get("warranty_data", {})

            if expected_st == "NOT_FOUND":
                if not w_data.get("found", True):
                    warranty_precision_hits += 1
                    is_success = True
                    relevance = 1.0
            else:
                if w_data.get("found") and w_data.get("status") == expected_st:
                    warranty_precision_hits += 1
                    is_success = True
                    relevance = 1.0

        elif cat == "Out-of-Domain":
            if res.get("fallback_triggered") or "support" in ans or "techpro" in ans:
                is_success = True
                relevance = 1.0
                retrieval_relevance_hits += 1

        else: # Product Specs, Troubleshooting, Multi-turn
            key_terms = item.get("key_terms", [])
            matched_terms = [kt for kt in key_terms if kt in ans]

            if sources:
                retrieval_relevance_hits += 1

            if len(matched_terms) > 0 or len(sources) > 0:
                is_success = True
                relevance = round(len(matched_terms) / max(len(key_terms), 1), 2)

        if is_success:
            successful_tasks += 1

        results.append({
            "id": q_id,
            "category": cat,
            "query": query,
            "intent": intent,
            "latency_ms": elapsed_ms,
            "success": is_success,
            "sources_count": len(sources),
            "relevance_score": relevance,
            "answer_preview": res.get("answer", "")[:120] + "..."
        })

    avg_latency = round(total_latency_ms / total_queries, 2)
    task_success_rate = round((successful_tasks / total_queries) * 100, 1)
    retrieval_relevance = round((retrieval_relevance_hits / max(total_queries - 5, 1)) * 100, 1)
    grounded_answer_rate = round((grounded_count / total_queries) * 100, 1)
    warranty_accuracy = round((warranty_precision_hits / 5) * 100, 1)

    summary = {
        "total_test_cases": total_queries,
        "task_success_rate": task_success_rate,
        "retrieval_relevance": min(retrieval_relevance, 100.0),
        "grounded_answer_rate": grounded_answer_rate,
        "warranty_accuracy": warranty_accuracy,
        "average_latency_ms": avg_latency,
        "unsupported_answer_rate": round(100.0 - grounded_answer_rate, 1),
        "detailed_results": results
    }

    return summary

if __name__ == "__main__":
    print("Running evaluation benchmark...")
    report = run_evaluation_benchmark()
    print(f"Task Success Rate: {report['task_success_rate']}%")
    print(f"Retrieval Relevance: {report['retrieval_relevance']}%")
    print(f"Warranty Accuracy: {report['warranty_accuracy']}%")
    print(f"Avg Latency: {report['average_latency_ms']} ms")
