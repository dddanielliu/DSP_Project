import hashlib
import os

import numpy as np
import pandas as pd
import psycopg2
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

PG_HOST = os.environ.get("PG_HOST", "localhost")  # 默認為 localhost
PG_PORT = os.environ.get("PG_PORT", "5432")      # 默認為 5432
PG_DATABASE = os.environ.get("PG_DATABASE", "lawdb")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "postgres") # 敏感資訊

PG_CONN_STRING = (
    f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} "
    f"host={PG_HOST} port={PG_PORT}"
)
# print(f"Database connection string assembled (excluding password): dbname={PG_DATABASE} user={PG_USER} host={PG_HOST} port={PG_PORT}")

_conn = None
_model = None
_text_splitter = None
def _init_resources():
    global _conn, _model, _text_splitter
    if _conn is None:
        _conn = psycopg2.connect(PG_CONN_STRING)
    if _model is None:
        MODEL_NAME = "intfloat/multilingual-e5-large"
        # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # print(f"Using device: {device}")
        _model = SentenceTransformer(
            MODEL_NAME,
            tokenizer_kwargs={"padding_side": "left"},
        )
    if _text_splitter is None:
        _text_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",           # 1. 結構性分隔 (多於一個換行符)
                "\n",             # 2. 單行換行符 (段落內換行)
                "；", ";",          # 3. 分號 (較長的語義單元)
                "。", "！", "？",  # 4. 中文句尾標點 (降級，除非段落過長才使用)
                ".\n", "!\n", "?\n",
                ". ", "! ", "? ", # 5. 英文句尾標點 (注意後接空格)
                "，", ",",          # 6. 逗號
                "、",              # 7. 頓號
                " ",               # 8. 空格
                ""                 # 9. 最差情況：強制字元切分
            ],
            chunk_size=500, chunk_overlap=200
        )
def generate_sha256_id(actname: str, chapter: str | None, article_no: str | None, subsection_no: str | None, chunk_index: int | None, content: str) -> str:
    """計算基於法條元數據和內容的 SHA-256 雜湊 ID"""
    # 將所有輸入參數合併成一個字串
    if chapter is None:
        chapter = ""
    if article_no is None:
        article_no = ""
    if subsection_no is None:
        subsection_no = ""
    if chunk_index is None:
        chunk_index = ""
    unique_string = f"{actname}-{chapter}-{article_no}-{subsection_no}-{chunk_index}-{content}"
    
    # 計算 SHA-256 雜湊並返回十六進位字串
    return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

def insert_chunk_and_commit(conn, actname: str, chapter: str | None, article_no: str | None, subsection_no: str | None, chunk_index: int | None, content: str, embedding: np.ndarray | None):
    """
    將單一 Chunk 及其向量插入到 PostgreSQL 資料庫，並立即提交 (COMMIT)。
    """
    cur = conn.cursor()

    primary_id = generate_sha256_id(actname, chapter, article_no, subsection_no, chunk_index, content)
    
    # 將 NumPy 向量轉換為 pgvector 期望的字串表示
    embedding_str = str(embedding.tolist()) if isinstance(embedding, np.ndarray) else None
    
    try:
        cur.execute(
            """
            INSERT INTO law_chunks 
            (id, law_name, chapter, article_no, subsection_no, chunk_index, content, embedding) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::VECTOR)
            """,
            (primary_id, actname, chapter, article_no, subsection_no, chunk_index, content, embedding_str)
        )
        # 關鍵：每次插入後立即提交
        conn.commit()
    except Exception as e:
        conn.rollback() # 發生錯誤時回滾該筆資料
        print(f"Error inserting {actname} - {chapter} - {article_no} - {subsection_no} (Index {chunk_index}): {e}")
        # 由於是逐條儲存，這裡可以選擇不拋出異常，繼續處理下一筆
    finally:
        cur.close()

def clean_value(value):
    """
    Convert invalid values to None:
    - NaN, pd.NA
    - None
    - empty strings or whitespace-only strings
    """
    if value is None:
        return None
    if pd.isna(value):  # handles np.nan and pd.NA
        return None
    if isinstance(value, str) and len(value.strip()) == 0:
        return None
    return value

def process_df(df: pd.DataFrame, lawname: str):
    """
    Process the DataFrame to insert law chunks and their embeddings into the database.
    """
    if not _model or not _conn or not _text_splitter:
        _init_resources()
    model = _model
    conn = _conn
    text_splitter = _text_splitter
    for rows in tqdm(df.itertuples(), total=len(df), desc=f"Processing {lawname}"):
        # content = rows[2]
        # embedding = model.encode(content)
        # print(f"Document: {content}\nEmbedding: {embedding[:5]}... (dim: {len(embedding)})\n")
        actname = clean_value(rows.actname) # 法條
        chapter = clean_value(rows.chapter) # 章
        title = clean_value(rows.title) # 第?條
        subsection_no = clean_value(rows.subsection) # 款號
        article = clean_value(rows.article) # 內容
        insert_chunk_and_commit(conn, actname, chapter, title, subsection_no, None, article, None)

        chunks = text_splitter.split_text(article)

        document_embeddings = model.encode(["passage: " + chunk for chunk in chunks])
        # print("embedding done")
        for i, vec in enumerate(document_embeddings):
            insert_chunk_and_commit(conn, actname, chapter, title, subsection_no, i, chunks[i], vec)
    
if __name__ == "__main__":
    _init_resources()
    model = _model
    text_splitter = _text_splitter
    conn = _conn
    # model.to(device)
    # print("start")
    # documents = [
    #     "The capital of China is Beijing.",
    #     "Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun.",
    #     "今天好天氣，我們去公園玩吧！",
    # ]
    # query_embeddings = model.encode(queries, prompt_name="query")
    # document_embeddings = model.encode(documents)
    # for doc, embedding in zip(documents, document_embeddings):
    #     print(f"Document: {doc}\nEmbedding: {embedding[:5]}... (dim: {len(embedding)})\n")


    for item in tqdm(os.listdir(os.path.join(os.path.dirname(__file__),"..","web_crawl","laws")), desc="Processing files"):
        # csv files
        df = pd.read_csv(os.path.join(os.path.dirname(__file__),"..","web_crawl","laws", item))
        process_df(df, lawname=item.split('_')[0])

    for item in tqdm(os.listdir(os.path.join(os.path.dirname(__file__),"..","web_crawl","pdfs")), desc="Processing PDF files"):
        pdf_file = os.path.join(os.path.dirname(__file__),"..","web_crawl","pdfs", item)
        loader = PyPDFLoader(pdf_file)
        data = loader.load()
        texts = text_splitter.split_documents(data)
        documents = [t.page_content for t in texts]
        actname = item.replace(".pdf", "")
        chapter = None
        title = None
        subsection_no = None
        insert_chunk_and_commit(conn, actname, chapter, title, subsection_no, None, "".join(documents), None)
        document_embeddings = model.encode(["passage: " + document for document in documents])
        for i, vec in enumerate(document_embeddings):
            insert_chunk_and_commit(conn, actname, chapter, title, subsection_no, i, documents[i], vec)
