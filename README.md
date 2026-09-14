# Employee Training Assistant

Small prototype for a grounded internal training assistant. The API accepts an employee question, retrieves approved source material, calls the configured Ollama-compatible LLM gateway, and returns an answer with citations.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload
```

Set these environment variables before using a live gateway:

```text
LLM_GATEWAY_URL=https://your-gateway.example
LLM_GATEWAY_API_KEY=your-key
LLM_MODEL=your-model-id
```

Without gateway settings, the app uses a deterministic local response so the API and tests work offline.

## API

```http
POST /chat
Content-Type: application/json

{"question":"How far in advance must I submit leave?"}
```

This is an intentionally narrow MVP. Replace the sample source repository with Bedrock Knowledge Bases and add authentication, persistence, trainer approval, and assessment tools as the product grows.
