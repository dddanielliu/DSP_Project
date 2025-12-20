# Taiwanese Occupational Safety and Health Regulations Knowledge Base and AI Assistant

## Project Description

This project develops a Retrieval Augmented Generation (RAG) system for querying Taiwanese occupational safety and health laws. The primary goal is to provide an intelligent assistant that can help users understand and navigate the complexities of OSH regulations, addressing the challenges of frequent occupational safety incidents stemming from a lack of crucial safety knowledge and difficulty in implementing law-compliant procedures.

The system encompasses several key components:

1.  **Web Crawling**: Automatically extracts legal documents, including structured articles from `law.moj.gov.tw` and related PDF documents, ensuring a comprehensive and up-to-date knowledge base.
2.  **Data Processing**: Utilizes advanced text splitting techniques and state-of-the-art `SentenceTransformer` models (specifically `intfloat/multilingual-e5-large`) to convert raw legal text into semantic vector embeddings.
3.  **Vector Database**: Stores these processed text chunks along with their high-dimensional vector representations in a PostgreSQL database, enhanced with the `pgvector` extension for efficient similarity search.
4.  **Retrieval System**: Implements a semantic search mechanism that, given a user query, retrieves the most relevant legal provisions by comparing the query's vector embedding with the stored law chunk embeddings.
5.  **API and Chatbot Integration**: Provides various user-friendly interfaces, including a FastAPI-based API and integrations with popular messaging platforms like LINE Bot and Telegram Bot, enabling interactive querying and information retrieval.
6.  **Evaluation and Learning Support**: Includes components for demonstrating and evaluating the system's performance, with a potential application in preparing for occupational safety basic examinations.

## Getting Started

To get a local copy up and running, follow these steps.

### Prerequisites

*   **Docker** and **Docker Compose**: Required for setting up the PostgreSQL database with `pgvector`.
*   **Python 3.11 or higher**: The primary programming language for the project.
*   **uv**: A fast Python package installer and resolver. Install it via `pip install uv`.
*   **.env file**: A `.env` file will be needed in `src/laws_database/` to configure PostgreSQL connection details. An example `.env` content:
    ```
    PG_HOST=localhost
    PG_PORT=5432
    PG_DATABASE=lawdb
    PG_USER=postgres
    PG_PASSWORD=postgres
    ```

### Installation and Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/DSP_Project.git
    cd DSP_Project
    ```
    (Replace `https://github.com/your-username/DSP_Project.git` with the actual repository URL)

2.  **Navigate to the `src/laws_database` directory and set up the database**:
    ```bash
    cd src/laws_database
    # Create the .env file with your PostgreSQL credentials
    # Use the docker-compose-dev.yml for development setup
    docker-compose -f docker-compose-dev.yml up -d postgres
    ```
    This will start a PostgreSQL container with the `pgvector` extension enabled and the `law_chunks` table schema initialized.

3.  **Install Python dependencies for all modules**:
    Navigate back to the project root directory and use `uv` to install dependencies.
    ```bash
    cd ../.. # Assuming you are in src/laws_database, go back to project root
    uv sync --with cpu # For CPU-only environment
    # or for ROCm GPU support (if applicable)
    # uv sync --with rocm
    ```

4.  **Crawl Legal Data**:
    ```bash
    cd src/web_crawl
    python crawler.py
    ```
    This script will crawl laws from `law.moj.gov.tw` based on URLs in `links.txt`, creating `laws` (CSV files of structured articles) and `pdfs` (downloaded PDF documents) directories within `src/web_crawl`.

5.  **Create Vector Embeddings and Populate the Database**:
    ```bash
    cd ../laws_database
    python create_vector.py
    ```
    This script processes the crawled `.csv` and `.pdf` files, generates semantic vector embeddings for the text chunks, and inserts them into the PostgreSQL `law_chunks` table.

6.  **Run a Similarity Search Demo**:
    ```bash
    python demo_similarity_search.py
    ```
    You will be prompted to enter queries, and the system will return the most semantically relevant law chunks from the database.

7.  **Run Evaluation/API/Chatbot (Optional)**:
    Refer to the specific documentation or scripts within the `src/evaluation` directory for instructions on running the API or chatbot integrations (e.g., `main.py`, `apidemo.py`, `line_bot.py`, `telegram_bot.py`).

## File Structure

The project is organized into several key directories:

*   `laws_database/`:
    *   `laws/`: Contains raw crawled `.csv` files of Taiwanese occupational safety and health regulations.
    *   `pdfs/`: Contains raw crawled `.pdf` documents related to the laws.
*   `src/`: Main source code directory, organized by functionality.
    *   `src/web_crawl/`:
        *   **Purpose**: Scripts for web crawling legal documents from `law.moj.gov.tw`.
        *   **Key Files**:
            *   `crawler.py`: The main script responsible for parsing web pages and extracting law content into CSVs and downloading PDFs.
            *   `links.txt`: A plain text file containing URLs of legal documents to be crawled.
    *   `src/laws_database/`:
        *   **Purpose**: Scripts for processing crawled data, generating vector embeddings, and managing the PostgreSQL database.
        *   **Key Files**:
            *   `create_vector.py`: Script to generate vector embeddings from the crawled data and populate the `pgvector` enabled PostgreSQL database.
            *   `demo_similarity_search.py`: A demonstration script to perform semantic similarity searches against the populated database.
            *   `docker-compose.yml`: Docker Compose configuration for production deployment of the PostgreSQL database.
            *   `docker-compose-dev.yml`: Docker Compose configuration for development environment, including PostgreSQL with `pgvector` and an `init.sql` for schema setup.
            *   `init.sql`: SQL script to initialize the PostgreSQL database schema, including the `law_chunks` table and `pgvector` extension.
            *   `pyproject.toml`: Python project configuration and dependency management for this module.
    *   `src/evaluation/`:
        *   **Purpose**: Contains scripts for evaluating the system's performance, API integration, and chatbot implementations.
        *   **Key Files**:
            *   `main.py`, `apidemo.py`, `demo.py`: Likely main entry points for API services or system demonstrations.
            *   `line_bot.py`, `telegram_bot.py`: Implementations for integrating the search functionality with LINE and Telegram chatbots.
            *   `test.ipynb`, `view_result.ipynb`: Jupyter notebooks for testing and visualizing evaluation results.
            *   `pyproject.toml`: Python project configuration and dependency management for this module.
    *   `src/question_crawl/`:
        *   **Purpose**: Potentially for crawling and processing legal questions or further extracting information from PDF documents.
        *   **Key Files**:
            *   `crawl.py`: Script related to crawling or extracting data for questions.
            *   `loadpdf.py`: Script for loading and processing PDF content.
            *   `pyproject.toml`: Python project configuration and dependency management for this module.
*   `DSP Project (shared).pdf`: This document provides the project vision, outlines the problem of occupational safety incidents, and includes sample test questions related to occupational safety regulations, suggesting the project's application in educational or assessment contexts.
*   `.git/`: Git version control system directory.
*   `.gitignore`: Specifies intentionally untracked files to ignore.
*   `README.md`: This README file, providing an overview of the project.

## Analysis

The core analysis method in this project revolves around **semantic similarity search** using **vector embeddings**.

*   **Text Preprocessing**: Legal documents are first processed using `langchain_text_splitters.RecursiveCharacterTextSplitter` to break down lengthy articles and PDF content into smaller, semantically coherent "chunks." This ensures that embeddings are generated for focused pieces of information.
*   **Embedding Generation**: Each text chunk is then transformed into a dense vector embedding using the `intfloat/multilingual-e5-large` model from the `sentence_transformers` library. This model is chosen for its effectiveness in multilingual text understanding and its ability to capture the semantic meaning of the text.
*   **Vector Database and Indexing**: The generated embeddings, along with their corresponding text chunks and metadata (law name, chapter, article number), are stored in a PostgreSQL database configured with the `pgvector` extension. An HNSW (Hierarchical Navigable Small Worlds) index is created on the embedding column (`CREATE INDEX ON law_chunks USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef_construction = 64);`) to enable highly efficient k-nearest neighbors (k-NN) search.
*   **Semantic Search**: When a user inputs a query, it is first embedded into a vector using the same `intfloat/multilingual-e5-large` model. This query embedding is then used to perform a similarity search against the stored law chunk embeddings in the database. The `pgvector` extension calculates the L2 (Euclidean) distance between the query embedding and all stored embeddings, retrieving the `top_k` most relevant law chunks.
*   **Filtering**: The search results are filtered to exclude entries marked as deleted (`content <> '（刪除）'`) and to prioritize actual content chunks (`chunk_index IS NOT NULL`), ensuring the relevance and quality of the retrieved information.

This approach allows the system to understand the semantic intent of user queries, rather than just keyword matching, and retrieve legal provisions that are conceptually related, even if they don't share exact wording.

## Results

[Provide a summary of your findings and conclusions, including any recommendations or implications for future research. Be sure to explain how your results address your research question or problem statement.]

## Contributors

[List the contributors to your project and describe their roles and responsibilities.]

## Acknowledgments

[Thank any individuals or organizations who provided support or assistance during your project, including funding sources or data providers.]

## References

[List any references or resources that you used during your project, including data sources, analytical methods, and tools.]
