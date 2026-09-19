FROM python:3.11-slim

RUN useradd -m -u 1000 user
RUN mkdir -p /app && chown -R user:user /app

USER user
ENV PATH="/home/user/.local/bin:$PATH"
RUN pip install --no-cache-dir --user uv

WORKDIR /app

COPY --chown=user:user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY --chown=user:user . /app

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 7860

CMD ["uv", "run", "python", "ui/app.py"]
