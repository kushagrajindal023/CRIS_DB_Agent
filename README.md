# 🚆 CRIS Database Agent

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20LLaMA--3.3--70b-orange)
![Google GenAI](https://img.shields.io/badge/Embeddings-Google%20GenAI-4285F4?logo=google&logoColor=white)
![ChromaDB](https://img.shields.io/badge/VectorStore-ChromaDB-6C3483)

> A conversational AI assistant that lets you query a real Indian Railway SQLite database using plain English. Powered by a custom **3-step RAG (Retrieval-Augmented Generation)** pipeline — no SQL knowledge required.

---

## 📌 Table of Contents

1. [Project Overview](#-project-overview)
2. [Features](#-features)
3. [How It Works — The RAG Pipeline](#-how-it-works--the-rag-pipeline)
4. [Tech Stack](#-tech-stack)
5. [Project Structure](#-project-structure)
6. [Prerequisites](#-prerequisites)
7. [Setup & Installation](#-setup--installation)
8. [Run in GitHub Codespaces](#-run-in-github-codespaces)
9. [Usage Guide](#-usage-guide)
10. [Example Queries](#-example-queries)
11. [Security Notice](#-security-notice)
12. [Contributing](#-contributing)

---

## 🌐 Project Overview

The **CRIS Database Agent** is a full-stack AI application that acts as a natural-language interface over a structured SQLite database of Indian Railway trains and stations. Instead of writing SQL, users type questions in plain English — the AI pipeline figures out which table and columns are relevant, generates a valid SQL query, executes it, and returns the results as a formatted table.

The application also ships with a built-in **admin CMS panel** that allows new data to be uploaded via CSV, managed by batch, and deleted — all without touching any code or restarting the server.

---

## ✨ Features

- 🤖 **Natural Language Querying** — Ask questions in plain English; the agent writes and executes the SQL.
- 🔍 **Custom RAG Pipeline** — A 3-step Retrieve → Augment → Generate loop grounded in real database schema.
- ⚡ **Groq-Powered LLM** — Sub-second response times using `llama-3.3-70b-versatile` via the Groq API.
- 🧬 **Google GenAI Embeddings** — High-quality semantic embeddings via `models/gemini-embedding-001`.
- 🗄️ **ChromaDB Vector Store** — In-memory vector database built live from the SQLite schema at startup.
- 📁 **Admin CMS Panel** — Upload any CSV to any table; the RAG index auto-refreshes on every upload.
- 🛡️ **Duplicate Upload Firewall** — Pre-flight check prevents the same file from being ingested twice.
- 🗑️ **Targeted Batch Deletion** — Remove a specific file's data by name; auto-drops empty tables on cleanup.
- 📊 **Live DB Stats** — Sidebar displays real-time row counts for all tables.
- 🔍 **SQL Transparency** — Every AI response includes a collapsible panel showing the generated SQL query.
- 🎨 **Dark Theme UI** — ChatGPT-style dark theme configured via `.streamlit/config.toml`.
- ☁️ **GitHub Codespaces Ready** — One-click cloud deployment via `.devcontainer/devcontainer.json`.

---

## ⚙️ How It Works — The RAG Pipeline

The core of `app.py` is a hand-crafted 3-step RAG loop. This gives precise control over retrieval quality and prompt structure, avoiding the unpredictability of a generic SQL agent.

```
User Question
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 1 — RETRIEVE (Schema Similarity Search)           │
│                                                         │
│  At startup, app.py reads every table from railway.db   │
│  via sqlite_master and PRAGMA table_info, then builds   │
│  a text description for each:                           │
│  "Table: trains. Columns: number, name, type, zone..."  │
│                                                         │
│  These descriptions are embedded with Google GenAI and  │
│  stored in a ChromaDB vector store (cached in session). │
│                                                         │
│  The user's question is embedded and compared against   │
│  the store → returns the single most relevant schema.   │
└─────────────────────────────────────────────────────────┘
      │  retrieved schema string
      ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 2 — AUGMENT (Prompt Construction)                 │
│                                                         │
│  A structured prompt is assembled:                      │
│  "Write SQL for '{question}' using this schema:         │
│   {retrieved_schema}. Always use LIKE with %            │
│   wildcards for text filtering. Return ONLY SQL."       │
└─────────────────────────────────────────────────────────┘
      │  augmented prompt
      ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 3 — GENERATE & EXECUTE                            │
│                                                         │
│  The prompt is sent to Groq (llama-3.3-70b-versatile,  │
│  temperature=0). The SQL response is stripped of        │
│  markdown fences, executed against railway.db via       │
│  pandas.read_sql_query(), and displayed as a            │
│  st.dataframe with a collapsible SQL inspector.         │
└─────────────────────────────────────────────────────────┘
      │  result DataFrame
      ▼
   User sees the answer
```

> **Hot-reload on upload:** When an admin uploads a new CSV, `st.cache_resource.clear()` is called immediately — forcing the RAG pipeline to re-index the updated schema before the next query. No restart required.

---

## 🛠️ Tech Stack

| Layer | Technology | Detail |
|---|---|---|
| **Frontend / UI** | [Streamlit](https://streamlit.io/) | Chat interface, sidebar admin panel, session state |
| **LLM** | [Groq API](https://console.groq.com/) via `langchain-groq` | `llama-3.3-70b-versatile`, `temperature=0` |
| **Embeddings** | [Google GenAI](https://aistudio.google.com/) via `langchain-google-genai` | `models/gemini-embedding-001` |
| **Vector Store** | [ChromaDB](https://www.trychroma.com/) via `langchain-community` | In-memory, rebuilt from schema at each session start |
| **Orchestration** | [LangChain](https://www.langchain.com/) | Embedding calls, vector store abstraction |
| **Source Database** | SQLite (`railway.db`) | Managed via `sqlite3` (stdlib) and `pandas` |
| **Data Handling** | [Pandas](https://pandas.pydata.org/) | CSV ingestion, `read_sql_query`, DataFrame display |
| **DB Adapter** | SQLAlchemy | LangChain ↔ SQLite URI interface |

---

## 📁 Project Structure

```
CRIS_db_agent/
│
├── app.py                  # ★ Main application: RAG pipeline, Streamlit UI,
│                           #     CMS admin panel, auto-ingestion logic
│
├── build_db.py             # One-time setup: downloads trains.json & stations.json
│                           #   from datameet/railways and builds railway.db
│
├── build_stations.py       # Post-setup utility: reads railway.db and generates
│                           #   stations.json as a lowercase name→code lookup dict
│
├── stations.json           # Committed to repo (19 KB). Station name → code map
│                           #   used for city-name translation in queries
│
├── requirements.txt        # Python package dependencies
│
├── .streamlit/
│   ├── config.toml         # ✅ Committed. Dark UI theme (ChatGPT-style palette)
│   └── secrets.toml        # ⚠️  NOT committed. Holds GROQ_API_KEY & GOOGLE_API_KEY
│
├── .devcontainer/
│   └── devcontainer.json   # GitHub Codespaces configuration (Python 3.11,
│                           #   auto-installs requirements, auto-launches app)
│
└── .gitignore              # Excludes: railway.db, trains.json, secrets.toml,
                            #   *.db, *.csv uploads, chroma_db/, venv/, etc.
```

> **Not tracked by Git:** `railway.db` (~1.1 MB), `trains.json` (~14.7 MB), and `.streamlit/secrets.toml` are all excluded via `.gitignore`. They must be generated or created locally.

---

## ✅ Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Python** | 3.11+ | [python.org](https://www.python.org/downloads/) |
| **Groq API Key** | — | Free at [console.groq.com](https://console.groq.com/) → API Keys |
| **Google API Key** | — | Free at [aistudio.google.com](https://aistudio.google.com/) → Get API key |
| **Git** | Any | For cloning the repository |

No local GPU or Ollama installation is required. Both the LLM and embeddings run entirely via free cloud APIs.

---

## 🚀 Setup & Installation

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/CRIS_db_agent.git
cd CRIS_db_agent
```

---

### Step 2 — Create & Activate a Virtual Environment

```bash
# Create the environment
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

**Packages installed:**

| Package | Role |
|---|---|
| `streamlit` | Web UI framework |
| `langchain` | Core orchestration |
| `langchain-community` | ChromaDB integration (`Chroma`) |
| `langchain-groq` | Groq LLM client (`ChatGroq`) |
| `langchain-google-genai` | Google embedding client |
| `chromadb` | Vector store engine |
| `pandas` | CSV ingestion and SQL result display |
| `sqlalchemy` | Database URI adapter for LangChain |

> **Linux / older Python only:** If you see a `sqlite3` version error from ChromaDB, uncomment `pysqlite3-binary` in `requirements.txt` and add these two lines to the very top of `app.py`:
> ```python
> __import__('pysqlite3')
> import sys
> sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
> ```

---

### Step 4 — Configure API Keys ⚠️

Create the file `.streamlit/secrets.toml`. The `.streamlit/` directory already exists in the repo; simply create `secrets.toml` inside it.

```toml
# .streamlit/secrets.toml
# ---------------------------------------------------------------
# ⚠️  NEVER commit this file. It is excluded by .gitignore.
# ---------------------------------------------------------------

GROQ_API_KEY    = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GOOGLE_API_KEY  = "AIzaSy_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

The application reads these at startup via:
```python
os.environ["GROQ_API_KEY"]    = st.secrets["GROQ_API_KEY"]
os.environ["GOOGLE_API_KEY"]  = st.secrets["GOOGLE_API_KEY"]
```

The app will crash with a `KeyError` if either key is missing or the file does not exist.

---

### Step 5 — Build the Railway Database *(first run only)*

```bash
python build_db.py
```

This script downloads `trains.json` and `stations.json` from the [datameet/railways](https://github.com/datameet/railways) repository (~14.7 MB total), creates `railway.db`, and populates two tables.

```
1. Downloading raw JSON data from GitHub...
2. Loading data into memory...
3. Building SQLite database schema...
4. Inserting data into tables (this might take a few seconds)...

Success! Database is built and ready.
Total Trains Inserted: XXXXX
Total Stations Inserted: XXXXX
```

> ℹ️ This only needs to be run **once**. The generated `railway.db` is reused on all future launches.

---

### Step 6 — (Optional) Rebuild the Station Lookup Map

`stations.json` is already committed to the repository and is ready to use. Only run this if you have significantly modified the `trains` table and need to regenerate the city-name → station-code translation dictionary.

```bash
python build_stations.py
```

---

### Step 7 — Launch the Application

```bash
streamlit run app.py
```

Open your browser and navigate to:

```
http://localhost:8501
```

---

## ☁️ Run in GitHub Codespaces

This repository is pre-configured for **one-click deployment** in GitHub Codespaces via `.devcontainer/devcontainer.json`.

1. On the repository page, click **Code → Codespaces → Create codespace on main**.
2. The container (Python 3.11 / Debian Bookworm) will start, automatically run `pip install -r requirements.txt`, and launch `streamlit run app.py`.
3. Codespaces will forward port `8501` and open a browser preview automatically.

> ⚠️ **Before launching**, you must add your API keys as **Codespaces Secrets** (not as a committed file):
> - Go to **GitHub → Settings → Codespaces → New secret**.
> - Add `GROQ_API_KEY` and `GOOGLE_API_KEY`.
> - Alternatively, create `.streamlit/secrets.toml` inside the codespace terminal after it starts.

---

## 📖 Usage Guide

### 💬 Chat Interface (Main Panel)

1. Type any question about trains or stations in the chat input at the bottom of the page.
2. The RAG pipeline retrieves the relevant schema, generates SQL, and executes it.
3. Results appear as an interactive table (`st.dataframe`).
4. Click **"🔍 See Generated SQL"** to inspect the exact query the AI wrote.
5. Use **"🧹 Clear Chat History"** in the sidebar to reset the session.

---

### 🔧 Admin CMS Panel (Sidebar)

#### Uploading New Data

1. In **"📁 Database Admin"**, type the target SQLite table name (e.g., `trains`, `employees`, `inventory`).
2. Upload a CSV file. A 3-row preview renders automatically.
3. Click **"Confirm & Upload"**.
   - ✅ **Success:** Data is appended to the table; the RAG index is automatically rebuilt.
   - ⚠️ **Blocked:** If the same filename was already uploaded to that table, the operation is aborted.

> Every uploaded row is automatically stamped with a `source_file` column containing the original filename. This is what enables targeted deletion.

#### Removing a Data Batch

1. In **"🗑️ Manage Uploads"**, type the name of the table to inspect.
2. A dropdown lists all distinct source files found in that table.
3. Select a file and click **"Delete Data"**.
   - All rows from that file upload are deleted via `DELETE FROM {table} WHERE source_file = ?`.
   - If the table becomes empty after deletion, it is **dropped automatically**.
   - The RAG index is rebuilt immediately.

---

## 💬 Example Queries

| Query | What it demonstrates |
|---|---|
| `"How many trains are in the database?"` | Aggregate `COUNT(*)` |
| `"Which train has the longest route by distance?"` | `ORDER BY distance DESC LIMIT 1` |
| `"Find all trains with 'Rajdhani' in their name"` | `LIKE '%Rajdhani%'` wildcard search |
| `"Which trains run from New Delhi to Mumbai?"` | City-name translation + route filtering |
| `"List all stations in the state of Karnataka"` | Column-filtered lookup on `stations` table |
| `"What is the travel duration of train 12626?"` | Point-lookup by specific train number |
| `"Show me all Shatabdi Express trains"` | Multi-row filtered result with `LIKE` |

---

## 🔒 Security Notice

> **Never commit the following files to a public repository.**

| File | Risk |
|---|---|
| `.streamlit/secrets.toml` | Contains live Groq and Google API keys |
| `railway.db` | Binary data file; regenerated by `build_db.py` |
| `trains.json` | Large raw source file (~14.7 MB); regenerated by `build_db.py` |
| Any uploaded `*.csv` files | May contain sensitive business data |

All of the above are covered by `.gitignore`. Before your first `git push`, run:

```bash
git status
```

None of the above should appear as tracked (green/staged) files. If any do, run:

```bash
git rm --cached <filename>
```

---

## 🤝 Contributing

Contributions are welcome. To contribute:

1. **Fork** the repository on GitHub.
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and commit with a descriptive message:
   ```bash
   git commit -m "feat: describe what you changed"
   ```
4. **Push** your branch and open a **Pull Request** against `main`.

Please ensure your changes do not introduce any committed secrets or large binary files. Run `git status` before pushing.
