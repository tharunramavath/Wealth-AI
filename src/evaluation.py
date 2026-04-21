import pandas as pd
import json
import logging
import os
from src.compliance import load_client_profile, validate_tickers
from src.nba_engine import generate_nba

logging.basicConfig(level=logging.INFO, format='%(message)s')

def evaluate_retrieval(queries, ground_truth):
    """
    Evaluates Hybrid RAG retrieval quality.
    Computes Precision@K and Recall@K.
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    
    logging.info("\n--- 🧐 Evaluating Hybrid RAG Retrieval Quality ---")
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        
        metrics = []
        for i, q in enumerate(queries):
            docs = retriever.invoke(q)
            retrieved_chunks = [str(doc.metadata.get('chunk_id')) for doc in docs]
            
            # Simulated Ground Truth for Demo (Assuming chunks 0, 1, 2 are correct)
            expected = ground_truth[i]
            
            true_positives = len(set(retrieved_chunks) & set(expected))
            precision_k = true_positives / len(retrieved_chunks) if retrieved_chunks else 0
            recall_k = true_positives / len(expected) if expected else 0
            
            metrics.append({
                "Query": q,
                "Precision@5": round(precision_k, 2),
                "Recall@5": round(recall_k, 2)
            })
            
        return pd.DataFrame(metrics)
            
    except Exception as e:
        logging.error(f"Vector store not found: {e}")
        return pd.DataFrame()

def run_llm_quality_evaluation():
    """ 
    Evaluates LLM Output Quality (Hallucination Rate, Compliance Enforcement, Confidence).
    """
    logging.info("\n--- 📊 Evaluating LLM Recommendation Engine (Automated) ---")
    
    if "GEMINI_API_KEY" not in os.environ or not os.environ["GEMINI_API_KEY"]:
        logging.warning("⚠️ GEMINI_API_KEY not set. Cannot run LLM evaluation.")
        return
        
    with open("data/clients/client_profiles.json", "r") as f:
        profiles = json.load(f)
        
    results = []
    
    allowed_tickers = ["HDFCBANK.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "BHARTIARTL.NS", "ITC.NS", 
                       "NIFTYBEES.NS", "GOLDBEES.NS", "LIQUIDBEES.NS", "AAPL", "MSFT", "TSLA", 
                       "GOOGL", "AMZN", "SPY", "QQQ", "GLD", "TLT", "VNQ", "Cash"]
                       
    hallucinations_detected = 0
    compliance_blocks = 0
    
    for p in profiles:
        logging.info(f"Testing Subject: {p['name']} ({p['risk_tolerance']})...")
        output = generate_nba(p["client_id"])
        
        if "error" in output:
            logging.error(f"  ❌ Generation Error: {output['error']}")
            continue
            
        score = output.get("confidence_score", 0.0)
        flags = output.get("flags", [])
        
        # Check hallucination specific
        if any("hallucinated" in f for f in flags):
            hallucinations_detected += 1
            
        if any("Violation" in f for f in flags):
            compliance_blocks += 1
            
        results.append({
            "client_id": p["client_id"],
            "risk_profile": p["risk_tolerance"],
            "confidence_score": score,
            "hallucination_flag": any("hallucinated" in f for f in flags),
            "compliance_blocked": any("Violation" in f for f in flags)
        })
        
    df = pd.DataFrame(results)
    
    logging.info("\n============== 📉 EVALUATION METRICS ==============")
    logging.info(f"Total Profiles Evaluated  : {len(df)}")
    
    if len(df) > 0:
        logging.info(f"Median Confidence Score   : {df['confidence_score'].median():.2%}")
        logging.info(f"Hallucination Rate        : {hallucinations_detected / len(df):.0%} of inferences")
        logging.info(f"Compliance Block Rate     : {compliance_blocks / len(df):.0%} of inferences")
        
        df.to_csv("data/processed/evaluation_report.csv", index=False)
        logging.info("Detailed payload exported -> data/processed/evaluation_report.csv")
    logging.info("===================================================\n")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # 1. RAG Evaluation (Offline)
    test_queries = [
        "What is the impact of rising inflation on Indian tech stocks?",
        "Gold price trends and safe haven assets."
    ]
    # Simulated Ground truth chunk IDs for testing
    ground_truth = [
        ["chunk_0001", "chunk_0002", "chunk_0005"],
        ["chunk_0006", "chunk_0008"]
    ]
    
    rag_metrics = evaluate_retrieval(test_queries, ground_truth)
    if not rag_metrics.empty:
        logging.info("\n" + rag_metrics.to_string(index=False))

    # 2. LLM Engine Evaluation (Online)
    run_llm_quality_evaluation()
