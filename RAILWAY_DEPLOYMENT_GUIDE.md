## Railway Setup Steps

1.  **Delete existing services**: If Railway already created a single service named `martin-system`, **delete it** from the project dashboard. This allows Railway to see your `railway.json` and create the 4 separate services instead.
2.  **Deploy**: Run `railway up` from your terminal.
3.  **Environment Variables**: Add your secrets (API keys) to the **Backend** service.

## Required Variables (Backend)

| Variable | Description | Recommended Value (Production) |
| :--- | :--- | :--- |
| `DATABASE_URL` | Postgres connection string | `${{Postgres.DATABASE_URL}}` (Railway default) |
| `REDIS_URL` | Redis connection string | `${{Redis.REDIS_URL}}` (Railway default) |
| `SECRET_KEY` | For JWT and encryption | A random 32+ char string |
| `JWT_SECRET_KEY` | Same as above | A random 32+ char string |
| `PINECONE_API_KEY` | Your Pinecone API Key | From Pinecone Dashboard |
| `PINECONE_INDEX_NAME` | Name of your Pinecone index | e.g. `ecowas-summit-knowledge` |
| `LLM_PROVIDER` | LLM backend to use | `openai` (Recommended for Cloud) |
| `OPENAI_API_KEY` | Your OpenAI API Key | From OpenAI Dashboard |
| `OPENAI_MODEL` | The model to use | `gpt-4-turbo-preview` |
| `CORS_ORIGINS` | Allowed frontend URLs | Your Railway frontend URL |

### Using Groq (Free & Fast Alternative to Ollama)
If you don't want to use OpenAI or local Ollama, you can use **Groq** for free:
1.  Get a key at [console.groq.com](https://console.groq.com/)
2.  Set these variables in Railway:
    *   `LLM_PROVIDER=openai`
    *   `OPENAI_API_KEY=your_groq_api_key_here`
    *   `OPENAI_BASE_URL=https://api.groq.com/openai/v1`
    *   `OPENAI_MODEL=llama3-8b-8192`

## Required Variables (Frontend)

| Variable | Description | Value |
| :--- | :--- | :--- |
| `VITE_API_URL` | The URL of your deployed backend | Your Railway backend URL |

## Optional (For Volumes)

If you want to persist uploaded documents, create a **Volume** in Railway and mount it to `/app/uploads` in the backend service.

---

> [!TIP]
> You can bulk import these by copying your local `.env` file (excluding `POSTGRES_` and `REDIS_` local settings) into the Railway "Bulk Import" UI.
