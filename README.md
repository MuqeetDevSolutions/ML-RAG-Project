# RAG Document QA

Ek document question-answering system jo PDF upload karne deta hai aur uske
content par sawaalon ke jawab deta hai — sirf document ke andar mojood
maloomat ke aadhar par (hallucination ke bagair).

## Tech Stack

- **Backend:** FastAPI
- **PDF extraction:** PyMuPDF
- **RAG pipeline:** LangChain
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, local + free)
- **Vector DB:** FAISS
- **LLM:** OpenAI API
- **Metadata DB:** SQLite (SQLAlchemy)
- **Frontend:** HTML + CSS + vanilla JavaScript

## Setup

1. Python 3.10+ install karo.
2. Repo clone karo.
3. Virtual environment banao: `python -m venv venv`
4. Activate karo: `venv\Scripts\activate` (Windows)
5. Dependencies install karo: `pip install -r requirements.txt`
6. `.env.example` ko copy karke `.env` banao aur apni API key daalo.
7. Server chalao: `uvicorn main:app --reload`
8. Browser me kholo: http://127.0.0.1:8000

## Project Structure

- `app/` — backend code
- `data/` — uploaded PDFs + FAISS index (git se ignore)
- `frontend/` — HTML/CSS/JS
- `tests/` — test scripts

## Status

Under development — built step by step.