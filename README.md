# 📚 RAG Document QA

A production-grade **Retrieval-Augmented Generation (RAG)** system that lets you upload PDF documents and ask questions about them — with **strict, source-grounded answers** and **zero hallucination**.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

- 📄 **PDF Upload & Processing** — extract, clean, and chunk text page-by-page
- 🔍 **Two-Stage Retrieval** — FAISS (bi-encoder) + Cross-encoder reranking
- 💬 **Conversational Memory** — follow-up questions work ("Who is Carl?" → "What about Susan?")
- 🎯 **Query Rewriting** — LLM converts vague follow-ups into standalone questions
- ✅ **Source Citations** — every answer shows exact file + page used
- 🛡️ **Zero Hallucination** — strict prompts + score thresholds
- 🔒 **Security** — prompt injection defense, file validation, rate limiting
- 📊 **Evaluation Framework** — metrics (hit rate, MRR, faithfulness)
- 🚀 **Production Ready** — logging, error handling, status monitoring

---

## 🏗️ Architecture
