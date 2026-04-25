from fastapi import FastAPI, Header, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import time

app = FastAPI(title="Lex-Advisor RAG Service API", version="1.0.0")


# --- Modele Pydantic conform Schemelor din YAML ---

class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model_id: str


class Chunk(BaseModel):
    chunk_id: uuid.UUID
    content: str = Field(..., max_length=4000)
    article_number: Optional[str] = None
    source_id: str
    namespace_id: str
    score: float


class Citation(BaseModel):
    marker: str
    chunk: Chunk


class QueryRequest(BaseModel):
    question: str = Field(..., max_length=2000)
    language: str  # In v1 doar "ro"
    namespaces: List[str]
    top_k: int = 10
    hint_article_number: Optional[str] = None
    include_answer: bool = True


class QueryResponse(BaseModel):
    request_id: uuid.UUID
    answer: Optional[str] = None
    citations: List[Citation]
    usage: Usage
    latency_ms: int
    model_version: str


# --- Endpoint-uri ---

@app.post("/v1/query", response_model=QueryResponse)
async def query(
        request: QueryRequest,
        x_request_id: uuid.UUID = Header(...),
        x_tenant_id: str = Header(...)
):
    start_time = time.time()

    # Aici va veni logica de Retrieval (Vector DB) și Generare (LLM)
    # Target p95: <= 4000ms

    # Exemplu de structură de răspuns gol (Empty-result contract)
    # Daca nu gasesti nimic: answer: null, citations: [], confidence: 0.0

    latency = int((time.time() - start_time) * 1000)
    return {
        "request_id": x_request_id,
        "answer": "Exemplu de răspuns bazat pe documente...",
        "citations": [],
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "model_id": "gemini-2.0-flash"
        },
        "latency_ms": latency,
        "model_version": "v1-alpha"
    }


@app.post("/v1/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(
        background_tasks: BackgroundTasks,
        x_request_id: uuid.UUID = Header(...),
        idempotency_key: uuid.UUID = Header(...)
):
    # Logica de procesare asincronă a documentelor
    job_id = f"j_{uuid.uuid4().hex[:8]}"
    return {
        "job_id": job_id,
        "status": "queued",
        "submitted_at": "2026-04-25T14:00:00Z"
    }


@app.get("/v1/health")
async def health():
    # Fast, unauthenticated check
    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": 3600,
        "dependencies": {
            "vector_store": "ok",
            "llm": "ok"
        }
    }



from datetime import datetime
from fastapi import BackgroundTasks

# Simulăm o bază de date pentru starea job-urilor
jobs_db = {}


def process_document(job_id: str, payload: dict, file_content: str = None):
    jobs_db[job_id]["status"] = "extracting"

    # 1. Extragere text (din URL sau File)
    # 2. Chunking bazat pe "Articolul X"
    # 3. Generare Embeddings (GDPR compliant)
    # 4. Salvare în Vector Store sub namespace-ul corect

    jobs_db[job_id]["status"] = "done"
    jobs_db[job_id]["completed_at"] = datetime.UTC().isoformat() + "Z"


@app.post("/v1/ingest", status_code=202)
async def start_ingest(
        payload: dict,  # Vei folosi schema IngestRequest definită anterior
        background_tasks: BackgroundTasks,
        idempotency_key: str = Header(...)
):
    # Verificăm dacă idempotency_key există deja pentru a returna același job_id
    job_id = f"j_{uuid.uuid4().hex[:8]}"

    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "submitted_at": datetime.UTC().isoformat() + "Z"
    }

    background_tasks.add_task(process_document, job_id, payload)

    return jobs_db[job_id]


import re
from typing import List, Dict


def split_legal_text(text: str, namespace_id: str, source_id: str) -> List[Dict]:
    """
    Împarte textul în fragmente bazate pe articole, extrăgând metadatele cerute.
    """
    # Regex pentru a identifica "Articolul 15", "Art. 15", "Articolul 15^1"
    # Folosim \b pentru limite de cuvânt și [ășțîâ] pentru diacritice
    article_pattern = r"(Articolul|Art\.)\s+([0-9]+(?:\^[0-9]+)?)"

    chunks = []

    # Split textul folosind pattern-ul de articol, dar păstrăm delimitatorul
    # (folosim paranteze în re.split pentru a păstra grupurile)
    raw_parts = re.split(f"({article_pattern})", text, flags=re.IGNORECASE)

    # re.split cu grupuri va returna: [text_pre, "Articolul 15", "Articolul", "15", text_articol, ...]
    # Iterăm pentru a reconstrui fragmentele
    i = 1
    while i < len(raw_parts):
        full_match_text = raw_parts[i]  # "Articolul 15"
        art_number = raw_parts[i + 2]  # "15"
        content_body = raw_parts[i + 3] if (i + 3) < len(raw_parts) else ""

        full_content = (full_match_text + content_body).strip()

        # Validăm limita de 4000 de caractere
        if len(full_content) > 4000:
            # Dacă e prea lung, îl tăiem la paragrafe, dar ideal e să rămână sub limită
            full_content = full_content[:3997] + "..."

        chunks.append({
            "chunk_id": str(uuid.uuid4()),  # Generat de provider
            "content": full_content,
            "article_number": art_number,
            "namespace_id": namespace_id,
            "source_id": source_id,
            "score": 0.0  # Se va popula la interogare
        })
        i += 4  # Salt peste grupurile capturate

    return chunks


from sentence_transformers import SentenceTransformer
import uuid

# Recomandat: Un model optimizat pentru limba română sau multilingv (ex: LaBSE sau paraphrase-multilingual)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def call_llm(question, search_results):
    pass


def calculate_cost(usage):
    pass


def create_embeddings_and_save(chunks: list, tenant_id: str):
    """
    Transformă fragmentele în vectori și îi stochează cu metadate.
    """
    for chunk in chunks:
        # Generăm vectorul pentru conținutul textului
        vector = model.encode(chunk["content"]).tolist()

        # Structura de salvare în Vector Store (ex: Pinecone, Milvus, Qdrant)
        point = {
            "id": chunk["chunk_id"],
            "vector": vector,
            "metadata": {
                "tenant_id": tenant_id,  # IZOLARE CRITICĂ
                "namespace_id": chunk["namespace_id"],
                "source_id": chunk["source_id"],
                "article_number": chunk["article_number"],
                "content": chunk["content"]  # Stocăm textul pentru a-l returna la Query
            }
        }
        # Codul de insert în baza de date vectorială aici...
        @app.post("/v1/query", response_model=QueryResponse)
        async def perform_query(
                request: QueryRequest,
                x_request_id: uuid.UUID = Header(...),
                x_tenant_id: str = Header(...)
        , vector_db=None):
            start_time = time.time()

            # 1. Transformăm întrebarea în vector
            query_vector = model.encode(request.question)

            # 2. Căutare în Vector DB cu filtrare pe tenant_id și namespace
            # Dacă avem hint_article_number, aplicăm un filtru de metadata
            search_results = vector_db.search(
                tenant_id=x_tenant_id,
                namespaces=request.namespaces,
                vector=query_vector,
                limit=request.top_k,
                article_hint=request.hint_article_number
            )

            # 3. Construim Prompt-ul pentru LLM (Exemplu de System Message)
            # "Răspunde DOAR în română, text simplu, fără bold/italic.
            # Folosește [1], [2] pentru a cita sursele de mai jos."

            # 4. Generare răspuns via LLM (ex: Gemini 2.5 Flash - menționat în documentație)
            llm_output = call_llm(request.question, search_results)

            latency = int((time.time() - start_time) * 1000)

            return {
                "request_id": x_request_id,
                "answer": llm_output.text,
                "citations": [
                    {"marker": f"[{i + 1}]", "chunk": res} for i, res in enumerate(search_results)
                ],
                "usage": {
                    "input_tokens": llm_output.usage.input,
                    "output_tokens": llm_output.usage.output,
                    "cost_usd": calculate_cost(llm_output.usage),
                    "model_id": "gemini-2.5-flash"
                },
                "latency_ms": latency,
                "model_version": "gemini-2.5-flash:2026-03"
            }

