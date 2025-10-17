
## Data Preprocessing

First put the crawled csv and pdfs by [web-crawl](../web-crawl/) to `./laws` and `./pdfs` (You can download from release file `law_crawled.zip`)

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
docker compose up --build -d
```

this will default to install torch-cpu

If you are AMD GPU and you want to use torch-rocm:

```
TORCH_VARIANT=rocm docker compose up --build -d
```

Then database is built.

You can start testing by entering text_db container

```
docker compose exec -it text_db bash
```

Activate virtural environment and run demo script

```
source .venv/bin/activate
python demo_similarity_search.py
```

## Manual deployment

Install Postgres 18 and pgvector

```bash
# Add PostgreSQL repository
echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
```

```bash
sudo apt install postgresql-18 postgresql-contrib-18
sudo apt insatll postgres-18-pgvector
```

After starting your postgres server

Then create database `lawdb`

```
createdb -U postgres lawdb
```

run law_chunks_backup.sql in your postgres by

```
psql -U postgres -d lawdb -f ./law_chunks_backup.sql
```

Then database is built.

You can start testing by creating and activating virtural environment.

First you need to install `uv`

After installing, run the following script to create a virtual environment:

```
uv sync
```

this will default to install torch-cpu

If you are AMD GPU and you want to use torch-rocm:


```
uv sync --extra rocm
```


Activating virtural environment

```
source .venv/bin/activate
```

Run demo script:

```
python demo_similarity_search.py
```
