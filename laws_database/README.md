
## Data Preprocessing

First put the crawled csv and pdfs by [web-crawl](../web-crawl/crawler.py) to `./laws` and `./pdfs` (You can download from release file `law_crawled.zip`)

`create_vector.py` will first go through each csv in `./laws`.

Then for each row, content will first go through chunker to about 500 words, then send to embedding model for embedding.

After embedding, each law_chunk will be saved to pgvector by its law_name, chapter, article_no, chunk_index, content, and embedding vector.

For pdfs, each pdf will load by PyPDFLoader, then go through RecursiveCharacterTextSplitter to split into chunks, then send to embedding model for embedding.

The actname will use pdf's filename, chapter and article_no will be None. Then also store to pgvector.

## Database exporting

For convience, you don't need to rebuild the database again every time.

I exported the database by:

```bash
docker compose -f docker-compose-dev.yml exec postgres pg_dump -U postgres -d lawdb > law_chunks_backup.sql
```

and generated `law_chunks_backup.sql` file, you can get it in release files

## Usage:

put `law_chunks_backup.sql` in current folder, then run

```
docker compose up -d
```

Then database is built.
