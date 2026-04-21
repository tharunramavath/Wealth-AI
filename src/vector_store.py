import os
import pandas as pd
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def build_vector_store():
    print("⏳ Loading embedding model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    print("DataLoader: Reading enriched chunks...")
    try:
        df = pd.read_csv("data/processed/classified_events.csv")
    except FileNotFoundError:
        print("❌ Error: classified_events.csv not found. Run previous steps first.")
        return

    docs = []
    for _, row in df.iterrows():
        metadata = {
            "chunk_id": str(row.get("chunk_id", "")),
            "source": str(row.get("source", "")),
            "sector": str(row.get("sector", "")),
            "event_type": str(row.get("event_type", "")),
            "dominant_sentiment": str(row.get("dominant_sentiment", "")),
            "published": str(row.get("published", ""))
        }
        text = f"Sector: {metadata['sector']} | Event: {metadata['event_type']} | Sentiment: {metadata['dominant_sentiment']} \n{str(row.get('text', ''))}"
        docs.append(Document(page_content=text, metadata=metadata))

    print(f"📦 Creating FAISS index for {len(docs)} documents...")
    vectorstore = FAISS.from_documents(docs, embeddings)
    
    vectorstore.save_local("faiss_index")
    print("✅ FAISS Vector Store saved to 'faiss_index/' directory.")
    
    # Quick retrieval test
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    test_q = "tech stocks and inflation"
    print(f"\n🔍 Testing retrieval: '{test_q}'")
    results = retriever.invoke(test_q)
    for i, res in enumerate(results):
        print(f"  [Result {i+1}] {res.page_content[:90]}... (Metadata: {res.metadata['sector']})")

if __name__ == "__main__":
    build_vector_store()
