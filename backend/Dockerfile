FROM python:3.13-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY ml-engine ml-engine
COPY data/metadata data/metadata
COPY research/results research/results
ENV PYTHONPATH=/app/backend:/app/ml-engine PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
