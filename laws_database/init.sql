-- init.sql
-- 這個腳本會在 PostgreSQL 容器啟動時自動執行。

-- 1. 啟用 pgvector 擴展
-- 這是讓 PostgreSQL 支援 VECTOR 資料類型和向量運算子的關鍵。
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 建立 law_chunks 資料表
-- 這張表用於儲存您所有的法條片段（Chunk）及相關資訊。
CREATE TABLE IF NOT EXISTS law_chunks (
    -- 自動遞增的主鍵
    id CHAR(64) PRIMARY KEY,
    
    -- 法規名稱 (Metadata for filtering)
    law_name TEXT NOT NULL,
    
    -- 章節名稱 (Metadata for filtering and display)
    chapter TEXT,

    -- 條文編號 (Metadata for filtering and display)
    article_no TEXT,

    -- 條文款項
    section_no INT,

    -- 片段索引 (如果一條法規被分成多個 Chunk)
    chunk_index INT NOT NULL,
    
    -- 實際的法條文本內容 (Text)
    content TEXT NOT NULL,
    
    -- 向量 Embedding (使用 pgvector 的 VECTOR 類型)
    -- 1536 是 OpenAI text-embedding-3-large 模型的維度。
    embedding VECTOR(1024)
);

-- 3. (選做) 建立索引
-- 為了高效的向量相似度搜尋 (k-Nearest Neighbors)，建議在 embedding 欄位上建立索引。
-- HNSW 索引適用於大多數 RAG 應用，提供最佳的性能-準確性權衡。
-- M=16, ef_construction=64 是一組常見的參數。
CREATE INDEX ON law_chunks USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef_construction = 64);

-- 或者，如果您擔心建表速度，可以先不建索引，在資料匯入完成後手動建立。
