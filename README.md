# AI Healthcare Customer Support (RAG)

Production-style healthcare support assistant using:

- Frontend: React + Tailwind CSS
- Backend: FastAPI
- RAG: sentence-transformers (`all-MiniLM-L6-v2`) + FAISS (`IndexFlatL2`)
- LLM: Gemini Flash or Claude Haiku

## Project Structure

```text
backend/
  main.py
  routes/
    chat.py
    metrics.py
  services/
    embeddings.py
    vector_store.py
    rag_pipeline.py
    intent.py
    triage.py
    sentiment.py
    llm_handler.py
  data/
    knowledge_base.json

frontend/
  src/
    App.jsx
    components/
      ChatUI.jsx
      Dashboard.jsx
    services/
      api.js
```

## Features Implemented

- Intent classification: `symptom | appointment | lab_report | billing | faq`
- Emotion detection: `anxious | frustrated | neutral`
- FAISS retrieval (`top_k=3`) from 100+ knowledge documents
- LLM generation constrained to retrieved context
- Confidence scoring from vector similarity
- Resolution logic (`confidence > 0.7` and context sufficiency)
- Symptom triage with urgency (`low | medium | high`)
- Emergency escalation messaging for high-risk terms
- Appointment department mapping + mock slots
- Lab report mini-explainer (hemoglobin / glucose patterns)
- Session memory of recent turns (last 3-5 messages)
- Real-time analytics endpoint for dashboard
- Mandatory medical disclaimer on every answer

## API

### POST `/chat`

Request:

```json
{
  "message": "My fever is not improving for 4 days",
  "session_id": "demo_123"
}
```

Response:

```json
{
  "answer": "string",
  "intent": "string",
  "confidence": 0.84,
  "urgency": "medium",
  "emotion": "anxious",
  "resolved": true,
  "sources": ["doc1", "doc2"]
}
```

### GET `/metrics`

Response:

```json
{
  "total_queries": 18,
  "resolved_queries": 14,
  "unresolved_queries": 4,
  "resolution_rate": 77.78,
  "emergency_cases_flagged": 2
}
```

## Run Locally

## 1. Backend

```powershell
cd "C:\Users\Lenovo\Documents\New project\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Set one LLM provider in `.env`:

- Gemini:
  - `LLM_PROVIDER=gemini`
  - `GEMINI_API_KEY=<your_key>`
- Claude:
  - `LLM_PROVIDER=claude`
  - `ANTHROPIC_API_KEY=<your_key>`

Start backend:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 2. Frontend

```powershell
cd "C:\Users\Lenovo\Documents\New project\frontend"
npm install
copy .env.example .env
npm run dev
```

Open: [http://localhost:5173](http://localhost:5173)

## Safety Notes

- The assistant never gives diagnosis.
- It always appends: `This is not medical advice. Please consult a doctor.`
- High-urgency symptom patterns trigger immediate emergency guidance.
