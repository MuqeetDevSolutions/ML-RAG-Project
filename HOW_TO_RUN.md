# 📖 HOW TO RUN — Complete Guide

**RAG Document QA Project — Step by Step Guide**

Yeh file aap ko sikhayegi:
- Project kaise kholo
- Server kaise chalao
- Application kaise use karo
- Common errors kaise fix karo

---

## 📋 Table of Contents

1. [Project Kaise Kholo](#1-project-kaise-kholo)
2. [Pehli Baar Setup](#2-pehli-baar-setup)
3. [Server Chalana](#3-server-chalana)
4. [Application Use Karna](#4-application-use-karna)
5. [Server Band Karna](#5-server-band-karna)
6. [Rozana Kaam Ka Flow](#6-rozana-kaam-ka-flow)
7. [Common Errors aur Fixes](#7-common-errors-aur-fixes)
8. [Project Structure](#8-project-structure)
9. [Important Files](#9-important-files)
10. [Testing Commands](#10-testing-commands)

---

## 1. Project Kaise Kholo

### Method 1: VS Code Se (Recommended)

1. **VS Code kholo**
2. Menu: **File → Open Folder…**
3. Apna folder select karo: `C:\Users\<YourName>\Desktop\rag_doc_qa`
4. **Select Folder** click karo
5. Agar "Do you trust the authors?" pooche → **Yes, I trust the authors**

### Method 2: Explorer Se

1. **Windows Explorer** kholo (`Win + E`)
2. Is path par jao: `Desktop\rag_doc_qa`
3. Folder me **right-click** → **Open with Code**

### VS Code Terminal Kholo

- Shortcut: **`Ctrl + ` `** (backtick)
- Ya menu: **Terminal → New Terminal**

Terminal neeche khulega — **Command Prompt** hona chahiye (PowerShell nahi).

> 💡 **Tip:** Agar PowerShell khul jaye aur error aaye, terminal ke dropdown (top-right) se **Command Prompt** select karo.

---

## 2. Pehli Baar Setup

> ⚠️ **Yeh sirf pehli baar karna hai.** Baad me skip karo aur seedha [Section 3](#3-server-chalana) par jao.

### Step 1: Virtual Environment Activate Karo

Terminal me:

```bash
venv\Scripts\activate
```

**Confirm karo:** Terminal ke shuru me `(venv)` dikhna chahiye:
```
(venv) C:\Users\YourName\Desktop\rag_doc_qa>
```

### Step 2: Dependencies Install Karo (agar nahi hain)

```bash
pip install -r requirements.txt
```

Yeh 5-10 minute lega **pehli baar**. Baad me skip karo.

### Step 3: `.env` File Check Karo

Project root me `.env` file honi chahiye. Agar nahi hai:

1. `.env.example` ko copy karo
2. Naam badal do: `.env`
3. Kholo aur apni **Groq API key** daalo:

```env
GROQ_API_KEY=gsk_YOUR_REAL_KEY_HERE
LLM_MODEL=openai/gpt-oss-20b
```

**Groq key kahan se:** https://console.groq.com/keys

### Step 4: PDF Upload Karo (Test ke liye)

`data\uploads\` folder me ek PDF rakho — jaise `sample.pdf`.

### Step 5: PDF Ko Process Karo (Ingest)

```bash
python tests\ingest_pdfs.py
```

Yeh PDF ko chunks me tod kar embeddings banayega. **Ek baar** chalta hai.

**Expected output:**
```
============================================================
  3. Processing: sample.pdf
============================================================
   Document ID:  a1b2c3d4...
   Pages:        200
   Chunks:       427
   Embeddings bana rahe hain...
   Added to store: 427 chunks
   >>> INGEST COMPLETE.
```

---

## 3. Server Chalana

### Har Baar Yeh Karna Hai (Naya Session)

**Step 1:** VS Code terminal kholo (`Ctrl + `` `)

**Step 2:** Project folder me jao (agar nahi ho):

```bash
cd Desktop\rag_doc_qa
```

**Step 3:** Venv activate karo:

```bash
venv\Scripts\activate
```

**Confirm:** `(venv)` dikhna chahiye.

**Step 4:** Server chalao:

```bash
uvicorn main:app --reload
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: [...]
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
[startup] SQLite database ready.
[startup] Security headers enabled.
INFO:     Application startup complete.
```

**Step 5:** Browser kholo:

- **Main app:** http://127.0.0.1:8000
- **API docs:** http://127.0.0.1:8000/docs
- **Status check:** http://127.0.0.1:8000/api/status

> 💡 **`--reload` ka matlab:** Code change karoge → server auto-restart ho jayega. Development ke liye.

### Pehli Baar Server Start Hone Me Zyada Time

Pehli baar chalane par **30-60 second** lagenge (embedding model load ho raha hai). **Aage se 2-3 second** hoga.

---

## 4. Application Use Karna

### Interface Overview

Jab aap http://127.0.0.1:8000 kholte ho:

```
┌─────────────────────────────────────────────────────┐
│  📚 RAG Document QA         [＋ New Chat] 🟢 Online │  ← Header
├────────────┬────────────────────────────────────────┤
│            │                                        │
│ DOCUMENTS  │  💬 Chat area                          │
│            │                                        │
│ 2 docs     │  ┌──────────────────────────────┐      │
│ 427 chunks │  │ Welcome message              │      │
│            │  └──────────────────────────────┘      │
│ [Upload]   │                                        │
│            │  ┌─ You: Who is Carl? ─────────┐       │
│ 📄 file1   │  └─────────────────────────────┘       │
│ 📄 file2   │  ┌─ Assistant ─────────────────┐       │
│            │  │ Carl is a watchmaker...     │       │
│            │  │ Sources: [page 81]          │       │
│            │  └─────────────────────────────┘       │
│            │                                        │
│            │  ┌──────────────────────┬───────┐      │
│            │  │ Sawaal likho...      │ [Ask] │      │
│            │  └──────────────────────┴───────┘      │
└────────────┴────────────────────────────────────────┘
```

### A) PDF Upload Karna

**Method 1: Click se**
1. Left sidebar me **"＋ Upload PDF"** button click karo
2. File selector khulega
3. Ek `.pdf` file select karo
4. **Open** click karo
5. Button red ho jayega "Processing…" — wait karo
6. Complete hone par: `427 chunks add hue (35.2s)`

**Method 2: Drag & Drop**
1. Apni PDF file Explorer se uthao
2. Left sidebar par **drop** karo
3. Automatically upload ho jayegi

**Processing time:**
- Chhota PDF (10 pages) → 3-5 second
- Bara PDF (200 pages) → 30-60 second
- **Sabr karo** — UI me loading dikhega

### B) Documents Dekhna

Left sidebar me:
```
📄 sample.pdf          ← File name
   427 chunks · 198 pages    ← Info
   ✕                    ← Delete button
```

**Statistic bar:**
```
2 documents
654 chunks total
```

### C) Document Delete Karna

1. Document ke aage **✕** button click karo
2. Confirmation dialog aayega
3. **OK** click karo
4. Document + uske chunks + disk se PDF — **sab delete**

### D) Sawaal Poocho

**Step 1:** Neeche wale input box me sawaal likho:
```
Who is Carl?
```

**Step 2:** **Ask** button click karo (ya **Enter** dabao)

**Step 3:** Loading dots dikhenge (3 bouncing dots) — **wait karo 2-5 second**

**Step 4:** Answer aayega:

```
┌─ Assistant ────────────────────────────────┐
│ Carl is a watchmaker in his 40s who lives  │
│ in Penzance, England. He runs his own      │
│ workshop where he fixes and makes watches. │
│                                            │
│ ✓ Found | top score 0.520 | 3.2s          │
│                                            │
│ SOURCES (4)                                │
│ ┌─────────────────────────────────────┐   │
│ │ 📄 sample.pdf  page 81  score 0.520│   │
│ │ "The Watch Chapter 1 – The Legend…" │   │
│ └─────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

### E) Follow-up Sawaal (Memory)

**Yeh KHAAS feature hai!** Aap pehle sawaal ke baad related sawaal pooch sakte ho:

**Turn 1:**
```
You: Who is Carl?
AI: Carl is a watchmaker...
```

**Turn 2:**
```
You: What about Susan?
AI: Susan is a security guard...   ← AI ne context samjha!
```

**Turn 3:**
```
You: What does she do?
AI: She watches boats near the beach...   ← "she" = Susan
```

**Yeh "conversation memory" hai.** AI ko pichle sawaalon ka pata hai.

### F) Naya Chat Shuru Karna

Header me **"＋ New Chat"** button click karo:
- Purani conversation memory se hata jayegi
- Fresh start
- Chat area clear ho jayega

### G) Out-of-Scope Test (Hallucination Check)

Sawaal jo **document me nahi hai**:

```
You: What is the capital of France?
AI: I could not find this information in the uploaded documents.
```

**Yeh sahi behavior hai!** AI jhoot nahi bolta — sirf document se jawab deta hai.

### H) Sources Kaise Padho

Har answer ke neeche **Sources section** hoga:

```
SOURCES (4)
┌────────────────────────────────────────────┐
│ 📄 sample.pdf  page 81  score 0.520       │
│ "The Watch Chapter 1 – The Legend Carl..." │
└────────────────────────────────────────────┘
┌────────────────────────────────────────────┐
│ 📄 sample.pdf  page 96  score 0.465       │
│ "you understand? I do, said Frank..."      │
└────────────────────────────────────────────┘
```

**Score ka matlab:**
- **0.7+** → Bohot relevant (high confidence)
- **0.5-0.7** → Related
- **0.3-0.5** → Thorا related
- **<0.3** → Filtr ho jate hain (nahi dikhte)

**Page number** = actual page jahan se answer aaya.

---

## 5. Server Band Karna

**Method 1:** Terminal me `Ctrl + C` dabao

**Method 2:** Terminal band karo (🗑️ icon)

**Expected:**
```
INFO:     Shutting down
INFO:     Application shutdown complete.
```

Agar error aaye "port already in use" next time:
- Koi purana process chal raha hai
- Task Manager kholo → Python processes end karo
- Ya: `netstat -ano | findstr :8000` chala kar PID dhoondho, phir `taskkill /PID <pid> /F`

---

## 6. Rozana Kaam Ka Flow

### Naye Din Ka Routine

1. **VS Code kholo** → `rag_doc_qa` folder
2. **Terminal kholo** (`Ctrl + `` `)
3. **Venv activate:**
   ```bash
   venv\Scripts\activate
   ```
4. **Server chalao:**
   ```bash
   uvicorn main:app --reload
   ```
5. **Browser me kholo:** http://127.0.0.1:8000
6. **Kaam karo** (PDF upload, sawaal poocho)
7. **Band karne ke liye:** `Ctrl + C`

### Naya PDF Add Karna (Existing Data Ke Sath)

```bash
# 1. Naya PDF data\uploads\ folder me daalo
# 2. Ingest chalao (append mode)
python tests\ingest_pdfs.py --append --skip-existing

# 3. Server restart karo (agar chal raha hai)
```

### Purana Data Clear Karna (Fresh Start)

```bash
# Option A: Sirf ek PDF delete karo (UI se)
# - Browser me document par ✕ click karo

# Option B: Sab kuch clear karo (command line)
python tests\ingest_pdfs.py --reset
```

---

## 7. Common Errors aur Fixes

### Error 1: `venv\Scripts\activate : The term is not recognized`

**Kyun:** Aap galat folder me ho ya venv nahi bana.

**Fix:**
```bash
# Pehle confirm karo ke aap rag_doc_qa folder me ho
cd
# Path ...\rag_doc_qa hona chahiye

# Agar venv folder nahi hai to banao
python -m venv venv

# Phir activate
venv\Scripts\activate
```

### Error 2: `uvicorn: command not found`

**Kyun:** Venv active nahi hai.

**Fix:**
```bash
# Terminal me (venv) dikhna chahiye
venv\Scripts\activate
uvicorn main:app --reload
```

Agar phir bhi fail:
```bash
python -m uvicorn main:app --reload
```

### Error 3: `ModuleNotFoundError: No module named 'X'`

**Kyun:** Koi library missing hai.

**Fix:**
```bash
pip install -r requirements.txt
```

Ya specific library:
```bash
pip install <library_name>
```

### Error 4: Port already in use

**Kyun:** Purana server chal raha hai.

**Fix:**
```bash
# Option 1: Different port use karo
uvicorn main:app --reload --port 8001
# Browser me: http://127.0.0.1:8001

# Option 2: Purana process band karo
# - Task Manager → Python process → End task
# - Ya:
netstat -ano | findstr :8000
taskkill /PID <PID_NUMBER> /F
```

### Error 5: Browser me blank page

**Kyun:** Frontend files missing ya path galat.

**Check:**
1. Browser me: http://127.0.0.1:8000/static/style.css kholo
2. Agar CSS dikhi → frontend theek hai
3. Blank page → **F12** dabao → **Console** tab → errors dekho

### Error 6: "Koi document upload nahi hua" chat me

**Kyun:** Store empty hai.

**Fix:**
```bash
# PDF ko process karo
python tests\ingest_pdfs.py

# Ya UI se upload karo
```

### Error 7: "LLM error: Groq authentication failed"

**Kyun:** API key ghalat ya missing.

**Fix:**
1. `.env` file kholo
2. `GROQ_API_KEY=gsk_...` check karo
3. https://console.groq.com/keys se nayi key lo agar zaroorat ho
4. **Server restart karo** (Ctrl+C, phir `uvicorn main:app --reload`)

### Error 8: "Rate limit reached"

**Kyun:** Groq free tier = 30 requests/minute.

**Fix:**
- 1 minute wait karo
- Ya `.env` me chota model:
  ```env
  LLM_MODEL=openai/gpt-oss-20b
  ```

### Error 9: Upload bohot slow (200-page PDF)

**Kyun:** Embedding model sab 427 chunks process kar raha hai.

**Solution:**
- **Sabr karo** — 30-60 second normal hai
- Progress bar dekho — ruka nahi
- Aage se `data/vectorstore/` cache ho jata hai

### Error 10: "Yeh asal me PDF nahi — detect: PNG image"

**Kyun:** Aap ne `.pdf` extension laga di lekin asal me image hai.

**Fix:**
- Asli PDF upload karo
- Ya image ko online converter se PDF banao

---

## 8. Project Structure

```
rag_doc_qa/
│
├── main.py                    ← FastAPI server entry point
├── requirements.txt           ← Dependencies list
├── .env                       ← API key (SECRET — git me nahi)
├── .env.example               ← Template
├── .gitignore                 ← Git ignore rules
├── README.md                  ← Project description
├── HOW_TO_RUN.md             ← Yeh file (guide)
│
├── app/                       ← Backend code
│   ├── api/                   ← HTTP endpoints
│   │   ├── documents.py       ← Upload, list, delete
│   │   ├── ask.py             ← Simple Q&A
│   │   └── chat.py            ← Chat with memory
│   ├── core/                  ← Core utilities
│   │   ├── config.py          ← Settings
│   │   ├── security.py        ← Security
│   │   ├── logging_config.py  ← Logs
│   │   ├── errors.py          ← Error handlers
│   │   └── status.py          ← Health checks
│   ├── db/                    ← Database
│   │   ├── models.py          ← Tables
│   │   ├── session.py         ← DB connection
│   │   └── repositories.py    ← CRUD
│   └── services/              ← Business logic
│       ├── pdf_reader.py      ← PDF extract
│       ├── text_cleaner.py    ← Text clean
│       ├── chunker.py         ← Chunking
│       ├── embedder.py        ← Embeddings
│       ├── vector_store.py    ← FAISS
│       ├── reranker.py        ← Reranking
│       ├── query_rewriter.py  ← Query rewrite
│       ├── llm.py             ← Groq LLM
│       ├── rag_pipeline.py    ← Full RAG
│       ├── conversation_store.py ← Chat memory
│       └── store_manager.py   ← Singleton
│
├── frontend/                  ← Web UI
│   ├── index.html             ← Page
│   ├── style.css              ← Styling
│   └── app.js                 ← Logic
│
├── data/                      ← Runtime data (git ignore)
│   ├── uploads/               ← User PDFs
│   ├── vectorstore/           ← FAISS index
│   └── app.db                 ← SQLite
│
├── logs/                      ← Application logs
│   └── app.log
│
├── tests/                     ← Test scripts
│   ├── ingest_pdfs.py         ← PDF processing
│   ├── query_store.py         ← Query test
│   ├── test_api.py            ← API tests
│   ├── test_rag_pipeline.py   ← RAG tests
│   ├── test_security.py       ← Security tests
│   ├── run_evaluation.py      ← Evaluation
│   └── eval_dataset.json      ← Test dataset
│
└── venv/                      ← Virtual environment (git ignore)
```

---

## 9. Important Files

### `.env` — **Sabse important**

```env
GROQ_API_KEY=gsk_your_real_key_here
LLM_MODEL=openai/gpt-oss-20b
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=800
```

**⚠️ Yeh file:**
- **KABHI** GitHub par upload mat karo
- **KABHI** kisi ko mat bhejo
- **KABHI** screenshot me mat dikhao

### `main.py` — Server ka entry point

Yahan se sab start hota hai. `uvicorn main:app` isi ko chalata hai.

### `data/uploads/` — Aap ki PDFs

Jo bhi PDF upload karte ho yahan aati hai.

### `data/vectorstore/` — Embeddings

FAISS index + metadata — yahan save hote hain. Delete karo → poori indexing dobara karni padegi.

### `data/app.db` — Chat history

Conversations aur documents ka metadata. Delete karo → chat history clear ho jayegi.

---

## 10. Testing Commands

### Health Check (Server chal raha hai?)

```bash
curl http://127.0.0.1:8000/health
```

Expected: `{"status":"ok","version":"0.8.0"}`

### Detailed Status

```bash
curl http://127.0.0.1:8000/api/status
```

Ya browser me: http://127.0.0.1:8000/api/status

Dekho:
- Database: OK
- Vector store: OK (kitne vectors)
- LLM: OK (key set hai?)
- Disk: OK (free space)

### Sab Tests Chalana

```bash
# API tests
python tests\test_api.py

# RAG pipeline
python tests\test_rag_pipeline.py

# Security
python tests\test_security.py

# Production features
python tests\test_production.py

# Evaluation (full)
python tests\run_evaluation.py --delay 3.0
```

### Store Ki Status

```bash
python tests\list_documents.py
```

### Store Reset (Sab Clear)

```bash
python tests\ingest_pdfs.py --reset
```

### Store Delete (Ek Document)

```bash
python tests\ingest_pdfs.py --delete <document_id>
```

---

## 🎯 Quick Reference — Cheat Sheet

### Sabse Zaroori Commands

| Kaam | Command |
|---|---|
| **Server chalao** | `venv\Scripts\activate` phir `uvicorn main:app --reload` |
| **Server band** | `Ctrl + C` |
| **Browser** | http://127.0.0.1:8000 |
| **API docs** | http://127.0.0.1:8000/docs |
| **PDF process** | `python tests\ingest_pdfs.py` |
| **Store list** | `python tests\list_documents.py` |
| **Status check** | http://127.0.0.1:8000/api/status |

### Kabhi Bhool Na Karna

- ✅ Har naye terminal me: `venv\Scripts\activate`
- ✅ PDF upload ke baad: `python tests\ingest_pdfs.py`
- ✅ `.env` me API key kabhi share nahi
- ✅ Server band karna: `Ctrl + C`

---

## 🆘 Emergency — Sab Kuch Reset

Agar sab kuch toot gaya aur fresh start karna hai:

```bash
# 1. Server band karo (agar chal raha hai)
# Ctrl + C

# 2. Venv activate
venv\Scripts\activate

# 3. Store clear
python tests\ingest_pdfs.py --reset

# 4. Database delete
del data\app.db

# 5. Server restart
uvicorn main:app --reload

# 6. PDFs dobara ingest
python tests\ingest_pdfs.py
```

**⚠️ Warning:** Yeh **poora data delete** kar dega:
- Saari conversations
- Saare documents ka metadata
- Saare embeddings

**PDFs `data/uploads/` me safe rahengi** — unhe dobara ingest karna padega.

---

## 📞 Kuch Aur Chahiye?

Agar is guide me kuch missing hai ya kuch samajh nahi aaya:

1. `README.md` padho — features + tech stack ke liye
2. `.env.example` dekho — config options ke liye
3. `/docs` kholo (browser) — API endpoints ke liye

---

**🎉 Happy coding! Aap ka project ready hai!**

Yeh guide hamesha rakhna — kabhi bhi confusion ho, ise kholo.

**Last updated:** Phase 18 complete