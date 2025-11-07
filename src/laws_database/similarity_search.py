import os
import sys
from typing import Annotated, Optional

import psycopg2
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.tools import tool
from langchain_core.documents import Document
from langchain_ollama import ChatOllama, OllamaLLM
from sentence_transformers import SentenceTransformer

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

# ------------------ Local LLM ------------------
# LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-oss:120b")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-oss:20b")

# ------------------ Load Embedding Model ------------------
MODEL_NAME = "intfloat/multilingual-e5-large"

AUTO_ADD_LAW = False if os.environ.get("AUTO_ADD_LAW", "0") == "0" else True

if AUTO_ADD_LAW:
    from .add_single_law import add_single_law

class SimilaritySearch:
    def __init__(self):
        self.model = SentenceTransformer(
            MODEL_NAME,
            tokenizer_kwargs={"padding_side": "left"},
        )
    
    # ------------------ Query Function ------------------
    def query_top_k_law_chunks(self, query: str, top_k: int = 5, law_name_filter: str | None = None) -> list[tuple]:
        """Return top-k most relevant law chunks, optionally filtered by an exact law_name."""
        # Compute embedding of the query
        query_embedding = self.model.encode(["query: "+query])[0]
        embedding_str = str(query_embedding.tolist())  # convert to PostgreSQL array format

        # Connect to PostgreSQL
        conn = psycopg2.connect(PG_CONN_STRING)
        cur = conn.cursor()

        # pgvector similarity search
        # --- 動態建立 SQL ---
        base_sql = """
        SELECT id, law_name, chapter, article_no, subsection_no, chunk_index, content, embedding
        FROM law_chunks
        WHERE chunk_index IS NOT NULL
        AND content <> '（刪除）'
        """
        
        # 使用參數化查詢來避免 SQL 注入
        params = []
        
        if law_name_filter:
            base_sql += " AND law_name = %s"
            params.append(law_name_filter)
            # params.append(f"%{law_name_filter}%")  # 法規名稱過濾改成模糊比對（避免 0 筆結果）
            # print(f"[SimilaritySearch] Applying filter: law_name = {law_name_filter}")

        base_sql += " ORDER BY embedding <-> %s::vector LIMIT %s;"
        params.extend([embedding_str, top_k])
        
        cur.execute(base_sql, tuple(params)) # 確保 params 是 tuple
        # --- SQL 建立結束 ---
        
        results = cur.fetchall()

        cur.close()
        conn.close()
        
        return results

    def get_top_k_law_chunks(self, query: str, top_k: int = 10, law_name_filter: str | None = None) -> list[dict]:
        result = self.query_top_k_law_chunks(query, top_k, law_name_filter)
        
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
    
    def get_law_documents(self, query: str, top_k: int = 10, law_name_filter: str | None = None) -> list[Document]:
        """Convert retrieved law chunks into LangChain Document format."""
        chunk_results = self.get_top_k_law_chunks(query, top_k, law_name_filter)
        print(f"[SimilaritySearch] Retrieved {len(chunk_results)} chunks for query='{query}' with law_name_filter='{law_name_filter}'")

        if len(chunk_results) == 0:
            try:
                with open(os.path.join(os.path.dirname(__file__), "..", "web_crawl", "no_law_name_filter.txt"), "r", encoding="utf-8") as f:
                    existing_filters = f.read().splitlines()
            except FileNotFoundError:
                # File doesn't exist yet, so no need to check existing entries
                existing_filters = []

            # 2. Write to the file only if it's a new entry
            if law_name_filter not in existing_filters:
                with open(os.path.join(os.path.dirname(__file__), "..", "web_crawl", "no_law_name_filter.txt"), "a", encoding="utf-8") as f:
                    f.write(f"{law_name_filter}\n")
        
            if law_name_filter is not None and AUTO_ADD_LAW:
                print(f"[SimilaritySearch] Attempting Auto-adding '{law_name_filter}'")
                # 嘗試自動新增法規連結
                add_single_law(law_name_filter)
                # print(f"[SimilaritySearch] Re-attempting retrieval after Auto-adding '{law_name_filter}'")
                # 再次嘗試檢索
                chunk_results = self.get_top_k_law_chunks(query, top_k, law_name_filter)
                print(f"[SimilaritySearch] Retrieved {len(chunk_results)} chunks after Auto-adding for query='{query}' with law_name_filter='{law_name_filter}'")


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

similarity_search = SimilaritySearch()

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
        "- 最終答案應該清楚明確，若是選擇題僅回覆選項數字或選項英文字母。\n"
        "- 先給出『直接回答』，再以條列說明依據與理由。\n"
        "- 每個關鍵結論後以來源編號標注，例如 [#1][#3]（對應下方檢索結果的編號）。\n"
        "- 優先引用與問題最相關的條文，避免大段貼文或逐字拷貝。\n"
        "- 文末列出『參考來源』清單（[#n] 法規名 第X條）。\n\n"
        f"【檢索結果】\n{context_text}\n\n"
        f"【問題】\n{query}\n\n"
        "【輸出格式】\n"
        "1) 最終答案：...\n"
        "2) 直接回答：...\n"
        "3) 依據與說明：\n- ...\n- ...\n"
        "4) 參考來源：[#n] 法規名 第X條；[#m] ...\n"
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

def manual_retrieve_context(
    query: Annotated[str, "The semantic query to search for relevant law context."],
    law_name: Annotated[Optional[str], "An optional EXACT law name to filter by (e.g., '危害性化學品標示及通識規則')."] = None
):
    """Retrieve law context documents to help answer a query.

    輸入: query (str)
    輸出: (serialized_str, documents)
      - serialized_str: 將每份文件的來源與內容合併成可讀字串
      - documents: list[Document]
    """
    retrieved_docs = similarity_search.get_law_documents(query, top_k=10, law_name_filter=law_name)
    if not retrieved_docs:
        serialized = f"【資料庫無{law_name}】"
        return serialized, []
    serialized = _serialize_documents_for_context(retrieved_docs)
    return serialized, retrieved_docs

@tool(response_format="content_and_artifact")
def retrieve_context(
    query: Annotated[str, "The semantic query to search for relevant law context."],
    law_name: Annotated[Optional[str], "An optional EXACT law name to filter by (e.g., '危害性化學品標示及通識規則')."] = None
):
    """Retrieve law context documents to help answer a query.

    輸入: query (str)
    輸出: (serialized_str, documents)
      - serialized_str: 將每份文件的來源與內容合併成可讀字串
      - documents: list[Document]
    """
    return manual_retrieve_context(query, law_name)

_model = None

def _init_model(
    verbose: bool = True,
    model_name: str = LLM_MODEL,
):
    global _model
    _model=ChatOllama(
        model=model_name,
        temperature=0.2,
        num_ctx=131072,
        verbose=verbose,
        num_predict=1200,
        streaming=True,
    )

def create_law_assistant_agent(verbose=True, config=None, model_name=LLM_MODEL):
    if _model is None:
        _init_model(verbose=verbose, model_name=model_name)
    agent = create_agent(
        model = _model,
        tools=[retrieve_context],
        system_prompt=(
            """
            你是一位精通《中華民國職場安全衛生相關法規》的專業法務助理。  
            你的任務是根據使用者提供的問題與法規內容，進行法規檢索與語意整合分析，並依據檢索到的內容給出最正確的答案。  

            請嚴格遵守以下規則：  

            一、檢索規則（**常識判斷與嚴格限制**）  
            1. **常識性問題處理：** 如果問題屬於職場安全衛生或環境保護領域的**基礎常識或普遍接受的概念**（例如：職業災害的直接原因、安全衛生的基本原則），**且你有高度信心直接回答，還是要認看看 `retrieve_context` 工具來檢索確認**，如果沒有結果，就進入「二、回答規則」。
            2. 你**僅能**使用 `retrieve_context` 工具來檢索法規，您可以自行決定要使用幾次、如何使用。
            3. 總共最多只能使用 **5 次** `retrieve_context` 工具。
            4. 若第一次檢索結果不足或不相關，請嘗試：  
                - 對每一個選項分別使用 `retrieve_context` 搜尋；或  
                - 使用問題中的**主要關鍵詞**進行精準搜尋。  
            5. 若題目明確提及某部法規或需針對特定法條查詢時，請務必在呼叫 `retrieve_context` 時加入 `law_name` 參數。  
                - **範例：** `retrieve_context({"query": "危害性化學品標示", "law_name": "危害性化學品標示及通識規則"})`  
            6. **不得重複查詢相同內容或使用過長的無效查詢。** 7. 若 5 次檢索後仍不足以回答，請明確說明資訊不足，並根據所有檢索結果給出「最合理的推論性答案」。  

            二、回答規則  
            1. **最終答案**必須**僅根據**檢索到的法規內容作答。但如果是依據「一、檢索規則」第 1 點判斷為常識性問題而直接作答，則不在此限。
            2. 若查無任何相關法規依據（且非常識性問題），請於答案前說明「查無相關法規依據，以下內容為基於常識知識或經驗的推論性答案」。  
            3. 若題意涉及法條解釋衝突，應根據「特別法優於普通法」原則給出結論。  

            三、回答格式（**極度嚴格**）  
            1. **工具呼叫 (Tool Call) 限制：** 呼叫工具時，JSON 輸出的內容必須是**精簡且高度相關**的關鍵詞組合。**嚴禁**在 `query` 參數中出現任何重複、冗餘、不相關或過長的字串。
            2. **最終答案格式：** 最終答案**只回覆數字或英文選項**。
            3. **輸出規範：**
                - 最終答案前請輸出一個**|字元**。
                - 僅回答**數字**或**英文字母**（例如：1, 2, 3, 4, A, B, C, D...）。
                - 若為複選題，請依照數字或英文字母順序輸出，**中間不得包含空白、逗號或換行**。
                - 若題目使用全形或特殊符號（如①），請轉換成對應的數字或英文字母（如 1）。

            四、特別警示  
            **不得使用 `retrieve_context` 工具超過 5 次。**
            **最終答案務必不包含任何其他文字，僅包含**|**加上選項代號(**數字**或**英文字母**)，並非選項內容。
            """
        ),
        middleware=[
            ToolCallLimitMiddleware(
                tool_name="retrieve_context",  # Limit specific tool
                thread_limit=None,  # Max 5 calls per thread
                run_limit=10,  # Max 3 calls per run
                exit_behavior="end"  # Gracefully end instead of error
            )
        ],
    )
    if config:
        agent.config = config
    return agent
