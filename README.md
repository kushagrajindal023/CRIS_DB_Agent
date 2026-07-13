# 🚆 Railway Database RAG Agent

> A **Retrieval-Augmented Generation (RAG)** assistant that enables natural-language querying of Indian Railway data. Powered by a custom 3-step RAG pipeline using Groq (LLM), Google GenAI (embeddings), and ChromaDB (vector store) — all served through a Streamlit web interface.

---

## 📌 Table of Contents

1. [Project Overview](#-project-overview)
2. [Technical Highlights](#-technical-highlights)
3. [Tech Stack](#-tech-stack)
4. [Project Structure](#-project-structure)
5. [Setup](#-setup)
6. [How to Run](#-how-to-run)
7. [Example Questions](#-example-questions)
8. [Security Notice](#-security-notice)
9. [Troubleshooting](#-troubleshooting)

---

## 🌐 Project Overview

The Railway Database RAG Agent is a conversational AI application that allows users to ask questions about Indian Railway train schedules, routes, and stations in plain English — no SQL knowledge required.

Unlike a traditional SQL agent that generates and executes raw queries, this system uses a **custom 3-step Retrieval-Augmented Generation (RAG) pipeline**:

1. **Retrieve** — the user's question is embedded and used to semantically search a ChromaDB vector store, fetching the most contextually relevant records from the railway database.
2. **Augment** — the retrieved records are injected as structured context into a carefully engineered prompt template.
3. **Generate** — the augmented prompt is sent to a Groq-hosted LLM, which synthesizes a precise, grounded natural-language answer.

This architecture means the LLM's response is always **anchored to real data** retrieved from the local SQLite database — it cannot hallucinate records that don't exist.

---

## ✨ Technical Highlights

### 🔍 Custom 3-Step RAG Pipeline
The core of the application is a hand-crafted RAG loop rather than a generic LangChain agent. This gives fine-grained control over retrieval quality, context window usage, and prompt structure — avoiding the unpredictability of fully autonomous SQL agents.

### ⚡ Groq-Powered LLM Inference
The application uses `langchain-groq` to call Groq's inference API, delivering extremely low-latency responses from models like `llama3-8b-8192` or `mixtral-8x7b-32768` without requiring local GPU hardware.

### 🧬 Google GenAI Embeddings
User queries and database records are encoded using Google's `text-embedding-004` model via `langchain-google-genai`, producing high-quality semantic embeddings for accurate similarity search.

### 🗄️ ChromaDB Vector Store
Retrieved embeddings are stored and queried using ChromaDB, a lightweight, persistent vector database that requires no external server — it runs entirely on disk alongside your application.

### 🔒 Secrets Management via Streamlit
API keys are stored in `.streamlit/secrets.toml`, which is excluded from version control. This is the recommended, idiomatic pattern for managing secrets in Streamlit applications.

---

## 🛠️ Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend / UI** | [Streamlit](https://streamlit.io/) | Chat interface and session management |
| **LLM** | [Groq API](https://groq.com/) via `langchain-groq` | Fast cloud-hosted language model inference |
| **Embeddings** | [Google GenAI](https://ai.google.dev/) via `langchain-google-genai` | Semantic text embeddings |
| **Vector Store** | [ChromaDB](https://www.trychroma.com/) | Local persistent vector database |
| **Orchestration** | [LangChain](https://www.langchain.com/) | RAG pipeline, prompt templates, chain composition |
| **Source Database** | SQLite (`railway.db`) | Structured railway data store |
| **Data Handling** | [Pandas](https://pandas.pydata.org/) | Data loading and pre-processing |

---

## 📁 Project Structure

```
CRIS_db_agent/
│
├── app.py                  # Main Streamlit application & RAG pipeline
├── railway_agent_free.py   # Standalone CLI version
├── build_db.py             # One-time script to build railway.db from raw data
├── build_stations.py       # One-time script to generate stations.json
│
├── stations.json           # Station name → code lookup map (committed)
├── requirements.txt        # Python package dependencies
│
├── .streamlit/
│   ├── config.toml         # Streamlit UI theme (committed)
│   └── secrets.toml        # ⚠️  API keys — NEVER commit this file
│
└── .gitignore              # Excludes railway.db, secrets.toml, venv, etc.
```

> **Note:** `railway.db` is generated locally by `build_db.py` and is excluded from version control. It must never be committed to a public repository.

---

## ⚙️ Setup

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/CRIS_db_agent.git
cd CRIS_db_agent
```

### Step 2 — Create a Virtual Environment

```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure API Keys

> ⚠️ **This step is critical.** The application will not start without valid API keys.

Create the secrets file at `.streamlit/secrets.toml`. The `.streamlit/` directory may already exist; if not, create it manually.

```toml
# .streamlit/secrets.toml
# -------------------------------------------------------
# ⚠️  NEVER commit this file to a public repository.
# It is excluded by .gitignore. Keep your keys private.
# -------------------------------------------------------

GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_API_KEY = "AIzaSy_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Where to get your keys:**
- **Groq API Key:** Create a free account at [console.groq.com](https://console.groq.com/) → API Keys → Create API Key.
- **Google API Key:** Visit [aistudio.google.com](https://aistudio.google.com/) → Get API key → Create API key in new project.

### Step 5 — Build the Railway Database *(first run only)*

```bash
python build_db.py
```

This downloads the raw railway JSON data and builds your local `railway.db` SQLite database. It only needs to be run once.

```
✅ Success! Database is built and ready.
Total Trains Inserted: XXXXX
Total Stations Inserted: XXXXX
```

---

## ▶️ How to Run

Once setup is complete, launch the Streamlit application:

```bash
streamlit run app.py
```

Open your browser and navigate to:

```
http://localhost:8501
```

Type a question about trains or stations in the chat input and the RAG agent will retrieve the relevant records from `railway.db` and generate a grounded answer.

---

## 💬 Example Questions

| Question | What it tests |
|---|---|
| `"How many trains are in the database?"` | Aggregate count over the full dataset |
| `"Which train has the longest route by distance?"` | Max-value retrieval |
| `"Find all trains with 'Rajdhani' in their name."` | Semantic text similarity search |
| `"Which trains run from New Delhi to Mumbai?"` | Route-based filtering with name translation |
| `"List all stations in Karnataka."` | State-level geographic lookup |
| `"What is the travel time for train 12626?"` | Point-lookup by specific train number |

---

## 🔒 Security Notice

> **Never commit the following files to a public repository:**

| File | Why |
|---|---|
| `.streamlit/secrets.toml` | Contains live API keys for Groq and Google GenAI |
| `railway.db` | Large binary data file; regenerated by `build_db.py` |
| `.env` | Alternative secrets file pattern |

All of the above are covered by the project's `.gitignore`. Before your first `git push`, run `git status` to confirm none of these files appear as tracked changes.

---

## 🔧 Troubleshooting

**`AuthenticationError` or `401 Unauthorized`**
→ Your API key in `.streamlit/secrets.toml` is missing, incorrect, or expired. Double-check the key values against your Groq and Google AI Studio dashboards.

**`ModuleNotFoundError`**
→ Your virtual environment is not active, or installation was incomplete. Run:
```bash
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

**`railway.db not found`**
→ Run `python build_db.py` to generate the database file before launching the app.

**ChromaDB `sqlite3` version error**
→ ChromaDB requires SQLite ≥ 3.35. If your system Python ships an older version, install `pysqlite3-binary` and add the following to the top of `app.py`:
```python
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
```

**Slow first response**
→ On the first run, ChromaDB builds its index from the database. Subsequent queries will be significantly faster.

---

## 📄 License

The Indian Railway dataset is sourced from [datameet/railways](https://github.com/datameet/railways) and is used under its respective open data license.
