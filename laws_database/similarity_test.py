import os
import json
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from langchain.tools import tool
from langchain_ollama import OllamaLLM

# ------------------ PostgreSQL Connection ------------------
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DATABASE = os.environ.get("PG_DATABASE", "lawdb")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres")

PG_CONN_STRING = (
    f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} "
    f"host={PG_HOST} port={PG_PORT}"
)

# ------------------ Local LLM (Ollama) ------------------
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-oss:20b")

# ------------------ Load Embedding Model ------------------
MODEL_NAME = "intfloat/multilingual-e5-large"

class SimilarityTest:
    def __init__(self):
        self.model = SentenceTransformer(
            MODEL_NAME,
            tokenizer_kwargs={"padding_side": "left"},
        )
    
    # ------------------ Query Function ------------------
    def query_top_k_law_chunks(self, query: str, top_k: int = 5) -> list[tuple]:
        """Return top-k most relevant law chunks for a given query string."""
        # Compute embedding of the query
        query_embedding = self.model.encode(["query: "+query])[0]
        print("embedding complete")
        print(query_embedding)
        embedding_str = str(query_embedding.tolist())  # convert to PostgreSQL array format

        # Connect to PostgreSQL
        conn = psycopg2.connect(PG_CONN_STRING)
        cur = conn.cursor()

        # pgvector similarity search using L2 (Euclidean distance)
        sql = f"""
        SELECT id, law_name, chapter, article_no, subsection_no, chunk_index, content, embedding
        FROM law_chunks
        WHERE chunk_index IS NOT NULL
        AND content <> '（刪除）'
        ORDER BY embedding <-> %s::vector
        LIMIT %s;
        """
        cur.execute(sql, (embedding_str, top_k))
        results = cur.fetchall()

        cur.close()
        conn.close()
        
        return results

    def get_top_k_law_chunks(self, query: str, top_k: int = 10) -> list[dict]:
        result = self.query_top_k_law_chunks(query, top_k)
        print(result)
        
        chunk_results = []
        for chunk in result:
            chunk_info = {
                "id": chunk[0],
                "law_name": chunk[1],
                "chapter": chunk[2],
                "article_no": chunk[3],
                "subsection_no": chunk[4],
                "chunk_index": chunk[5],
                "content": chunk[6],
                # "embedding": chunk[7],
            }
            chunk_results.append(chunk_info)
        
        return chunk_results
    
    def get_law_documents(self, query: str, top_k: int = 10) -> list[Document]:
        """Convert retrieved law chunks into LangChain Document format."""
        chunk_results = self.get_top_k_law_chunks(query, top_k)
        documents = [
            Document(
                page_content=chunk["content"],
                metadata={
                    # "id": chunk["id"],
                    "law_name": chunk["law_name"],
                    "chapter": chunk["chapter"],
                    "article_no": chunk["article_no"],
                    "subsection_no": chunk["subsection_no"],
                    "chunk_index": chunk["chunk_index"],
                },
            )
            for chunk in chunk_results
        ]
        return documents


# 在模組層級建立實例，供工具與主程式共用
similarity_test = SimilarityTest()

def _serialize_documents_for_context(docs: list[Document]) -> str:
    """將檢索文件序列化成可閱讀的上下文字串。"""
    lines: list[str] = []
    for idx, doc in enumerate(docs, start=1):
        meta = doc.metadata or {}
        source = (
            f"{meta.get('law_name', '')}"
            f" | Chapter: {meta.get('chapter', '')}"
            f" | Article: {meta.get('article_no', '')}"
            f" | Subsection: {meta.get('subsection_no', '')}"
            f" | Chunk: {meta.get('chunk_index', '')}"
        ).strip()
        lines.append(f"#[{idx}] Source: {source}\n{doc.page_content}")
    return "\n\n".join(lines)


def call_llm_with_context_via_langchain(query: str, docs: list[Document]) -> str:
    """優先透過 LangChain 的 Ollama 介面進行推論，回傳文字答案。"""
    context_text = _serialize_documents_for_context(docs)
    print(f"[LLM] Using LangChain OllamaLLM with model={LLM_MODEL}")
    print(f"[LLM] docs={len(docs)}, query_len={len(query)}, context_chars={len(context_text)}")
    print(f"[LLM] context_preview=\n{context_text[:2000]}{'...' if len(context_text)>2000 else ''}")
    prompt = (
        "你是一位精通中華民國職場安全法規的法務助理。請根據提供的法規片段，"
        "用繁體中文進行『語意整合』後回答問題，並嚴格遵循：\n"
        "- 只依據提供片段作答；資訊不足時請明確說明不足與需要的補充。\n"
        "- 先給出『直接回答』，再以條列說明依據與理由。\n"
        "- 每個關鍵結論後以來源編號標注，例如 [#1][#3]（對應下方檢索結果的編號）。\n"
        "- 優先引用與問題最相關的條文，避免大段貼文或逐字拷貝。\n"
        "- 文末列出『參考來源』清單（[#n] 法規名 第X條）。\n\n"
        f"【檢索結果】\n{context_text}\n\n"
        f"【問題】\n{query}\n\n"
        "【輸出格式】\n"
        "1) 直接回答：...\n"
        "2) 依據與說明：\n- ...\n- ...\n"
        "3) 參考來源：[#n] 法規名 第X條；[#m] ...\n"
    )
    llm = OllamaLLM(
        model=LLM_MODEL,
        temperature=0.2,
        num_ctx=8192,
        num_predict=1200,
        top_p=0.9,
        repeat_penalty=1.1,
    )
    return llm.invoke(prompt)

@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """Retrieve law context documents to help answer a query.

    輸入: query (str)
    輸出: (serialized_str, documents)
      - serialized_str: 將每份文件的來源與內容合併成可讀字串
      - documents: list[Document]
    """
    retrieved_docs = similarity_test.get_law_documents(query, top_k=10)
    serialized = _serialize_documents_for_context(retrieved_docs)
    return serialized, retrieved_docs

# ------------------ Demo ------------------
if __name__ == "__main__":
    try:
        print("Loading embedding model and preparing retriever...")
        while True:
            query = input("Enter your query: ").strip()
            if not query:
                continue

            # 1) 檢索前 10 筆最相關法規片段（dict 形式）
            chunk_dicts = similarity_test.get_top_k_law_chunks(query, top_k=10)
            print("\nTop 10 most relevant law chunks (dict):")
            print(chunk_dicts)

            # 2) 轉成 LangChain Document（供 LLM 使用）
            docs = [
                Document(
                    page_content=c["content"],
                    metadata={
                        "law_name": c["law_name"],
                        "chapter": c["chapter"],
                        "article_no": c["article_no"],
                        "subsection_no": c["subsection_no"],
                        "chunk_index": c["chunk_index"],
                    },
                )
                for c in chunk_dicts
            ]

            # 3) 使用 LangChain.Ollama 產生整合後回答
            try:
                answer = call_llm_with_context_via_langchain(query, docs)
                print("\n[LLM Answer]\n" + answer)
            except Exception as e:
                print(f"\n[LLM Error] {e}")

    except KeyboardInterrupt:
        print("\nExiting...")
