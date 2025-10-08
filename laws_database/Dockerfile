FROM python:3.12-slim AS downloader

# Install just the Hugging Face Hub CLI
RUN pip install --no-cache-dir "huggingface_hub[cli]"

# Download the model into a known path
RUN huggingface-cli download intfloat/multilingual-e5-large


FROM python:3.12-slim AS prod
RUN apt-get update && apt-get install -y \
    curl \
    tmux \
    git \
    && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && bash -c "source $HOME/.local/bin/env"
COPY --from=downloader /root/.cache/huggingface/ /root/.cache/huggingface/

WORKDIR /app


RUN --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=.python-version,target=/app/.python-version \
    bash -c "/root/.local/bin/uv sync"

COPY . .

CMD ["bash"]
