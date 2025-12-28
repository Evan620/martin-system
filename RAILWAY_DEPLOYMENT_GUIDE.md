# Railway Environment Variables Setup

To deploy the **ECOWAS Summit TWG System** on Railway, you need to configure the following environment variables in the Railway dashboard.

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

## Required Variables (Frontend)

| Variable | Description | Value |
| :--- | :--- | :--- |
| `VITE_API_URL` | The URL of your deployed backend | Your Railway backend URL |

## Optional (For Volumes)

If you want to persist uploaded documents, create a **Volume** in Railway and mount it to `/app/uploads` in the backend service.

---

> [!TIP]
> You can bulk import these by copying your local `.env` file (excluding `POSTGRES_` and `REDIS_` local settings) into the Railway "Bulk Import" UI.
