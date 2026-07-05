# 🤖 AI Database Agent — Conversational CMS with LLM-Powered Querying

> An enterprise-grade, **data-agnostic** AI assistant that turns any SQLite database into a natural-language API. Administrators upload CSVs through a built-in CMS panel; users chat with an AI agent powered by a local LLM to query that data in real time — no code, no SQL, no restarts required.

---

## 📌 Table of Contents

1. [Overview](#-overview)
2. [Key Architectural Features](#-key-architectural-features)
3. [Tech Stack](#-tech-stack)
4. [Project Structure](#-project-structure)
5. [Prerequisites](#-prerequisites)
6. [Installation & Setup](#-installation--setup)
7. [Usage Guide](#-usage-guide)
8. [Example Queries](#-example-queries)
9. [Troubleshooting](#-troubleshooting)
10. [License](#-license)

---

## 🌐 Overview

This project began as a domain-specific assistant for querying Indian Railway data. It has since evolved into a **fully data-agnostic conversational CMS** — a system where:

- **Administrators** control the database backend by uploading any structured CSV file through a sidebar panel, routing it into a named SQLite table on the fly.
- **Users** interact with the data exclusively through a natural-language chat interface, with no awareness of the underlying SQL schema.
- **The AI agent** (LangChain + Mistral via Ollama) dynamically introspects the entire live database schema and generates accurate SQL queries for any table it finds — **including tables created moments ago**.

This architecture decouples the AI layer from any hardcoded data model. Swapping the dataset requires nothing more than uploading a new CSV.

---

## ⚙️ Key Architectural Features

### 1. 🏗️ Dynamic Table Generation

The admin panel accepts any well-formed CSV file and writes it to the SQLite database using the table name specified by the administrator at upload time.

- If the target table **does not exist**, it is created automatically with the schema inferred from the CSV headers.
- If the target table **already exists**, new rows are safely appended (`if_exists='append'`), preserving all existing data.
- This requires **zero schema configuration** — the system adapts to the structure of whatever data you provide.

```python
# From app.py — Pandas handles dynamic schema inference and table creation
df.to_sql(target_table, conn, if_exists='append', index=False)
```

---

### 2. 🏷️ Data Tracking & Targeted Deletion ("Undo Upload")

Every row ingested through the admin panel is automatically stamped with a `source_file` metadata column containing the original filename of the CSV it came from.

```python
# From app.py — Applied before writing to the database
df['source_file'] = uploaded_file.name
```

This `source_file` column enables **surgical, batch-level deletions**: the "Manage Uploads" panel reads all distinct `source_file` values from any given table and presents them as a dropdown. Selecting one and confirming executes a targeted `DELETE` that removes precisely that batch of rows — functioning as a **reliable "Undo Upload"** operation without affecting any other data in the table.

```sql
-- The exact query executed on deletion
DELETE FROM {table_name} WHERE source_file = ?
```

---

### 3. 🛡️ Duplicate Upload Firewall

Before any data is written to the database, the system executes a pre-flight query to determine whether a file with the same name has already been loaded into the target table.

```python
# From app.py — The security check
cursor.execute(
    f"SELECT COUNT(*) FROM {target_table} WHERE source_file = ?",
    (file_name,)
)
if cursor.fetchone()[0] > 0:
    file_exists = True
```

- If the file has already been uploaded to that table, the operation is **aborted** and the administrator is shown an explicit warning — no duplicate rows are written.
- If the target table does not yet exist (i.e., it's a brand-new dataset), the `OperationalError` is caught gracefully and the upload proceeds as a first-time insertion.

This firewall prevents a common source of data corruption in any CMS: **accidental re-uploads of the same dataset**.

---

### 4. 🧠 Universal AI Querying (Schema-Agnostic Agent)

This is the core architectural upgrade. The LangChain agent is initialized **without** specifying `include_tables`, which means it receives the **full schema of the entire SQLite database** at inference time.

```python
# From app.py — Note the absence of include_tables
db = SQLDatabase.from_uri('sqlite:///railway.db')
```

A generalized prompt template instructs the LLM to first **analyze all available tables**, determine which one is relevant to the user's question, and then generate a valid SQL query targeting only that table's actual columns.

```python
_DEFAULT_TEMPLATE = """Given an input question, first create a syntactically
correct {dialect} query to run, then look at the results of the query and
return the answer.

STRICT SQL RULES:
1. Carefully analyze the available tables in {table_info} to determine which
   table contains the data needed to answer the question.
2. ONLY use the columns explicitly listed in the schema for the chosen table.
3. To find the highest, longest, or maximum, prefer using
   'ORDER BY column DESC LIMIT 1'.
4. If the user asks for data that does not exist in ANY table, return:
   "I cannot answer this as that specific data is not available."
...
"""
```

**The key consequence**: when an admin uploads a new CSV into a table called `employees`, a user can immediately ask *"Who is the highest-paid employee?"* — with no server restart and no code change. The agent discovers the new table's schema live.

---

### 5. 🔒 Input Safety Firewall

User queries are pre-processed through a `secure_clean_input()` function before reaching the LLM. This layer:

- **Blocks forbidden query categories** (e.g., `platform`, `ticket price`, `live status`, `fare`) by pattern matching, returning a safe canned response instead of hitting the LLM.
- **Translates natural language station names** to their official codes using an in-memory lookup dictionary (e.g., `"Delhi"` → `"NDLS"`), improving SQL query accuracy.

---

## 🛠️ Tech Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend / UI** | [Streamlit](https://streamlit.io/) | Chat interface, admin sidebar, session state |
| **AI / LLM** | [Ollama](https://ollama.com/) + Mistral | Local, offline LLM inference |
| **AI Orchestration** | [LangChain](https://www.langchain.com/) | Text-to-SQL agent (`SQLDatabaseChain`) |
| **Backend Database** | SQLite | Persistent, file-based relational database |
| **Data Handling** | [Pandas](https://pandas.pydata.org/) | CSV ingestion, schema inference, DataFrame operations |
| **DB Connector** | SQLAlchemy | LangChain ↔ SQLite interface |

---

## 📁 Project Structure

```
CRIS_db_agent/
│
├── app.py                  # Main application: Streamlit UI, CMS admin panel,
│                           #   LangChain agent initialization, chat loop
│
├── railway_agent_free.py   # Standalone CLI version of the AI agent
│
├── build_db.py             # One-time script: downloads raw JSON and builds
│                           #   the initial railway.db SQLite database
│
├── build_stations.py       # One-time script: generates the stations.json
│                           #   name-to-code lookup map
│
├── stations.json           # Station name → code mapping (committed to repo)
├── requirements.txt        # Python package dependencies
│
├── .streamlit/
│   └── config.toml         # Streamlit theme and UI configuration
│
└── .gitignore              # Excludes railway.db, trains.json, venv, etc.
```

> **Note:** `trains.json` (~14 MB) and `railway.db` (~1.1 MB) are excluded from version control via `.gitignore`. They are generated locally by running `build_db.py` on first setup.

---

## ✅ Prerequisites

Ensure the following are installed on your machine before proceeding.

| Requirement | Minimum Version | Notes |
|---|---|---|
| **Python** | 3.9+ | [python.org](https://www.python.org/downloads/) |
| **Ollama** | Latest | [ollama.com](https://ollama.com/download) — must be running as a service |
| **Git** | Any | For cloning the repository |

---

## 🚀 Installation & Setup

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

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt` installs:**
- `langchain`, `langchain-community`, `langchain-experimental` — AI orchestration
- `sqlalchemy` — Database connectivity layer
- `streamlit` — Web UI framework
- `pandas` — CSV and DataFrame operations

---

### Step 4 — Pull the Mistral Model via Ollama

Ensure the Ollama application is running (check your system tray or run `ollama serve`), then pull the model:

```bash
ollama pull mistral
```

> ⏳ This is a **one-time download** of approximately **4.4 GB**. Subsequent runs use the locally cached model.

Verify the model is ready:
```bash
ollama list
# Expected output: mistral:latest   ...
```

---

### Step 5 — Build the Initial Database *(Railway data only)*

If you are starting with the original Indian Railway dataset, run this script to download the raw data and populate `railway.db`:

```bash
python build_db.py
```

Expected output:
```
1. Downloading raw JSON data from GitHub...
2. Loading data into memory...
3. Building SQLite database schema...
4. Inserting data into tables...

✅ Success! Database is built and ready.
Total Trains Inserted: XXXXX
Total Stations Inserted: XXXXX
```

> ℹ️ **Skippable for custom datasets.** If you plan to use exclusively your own CSVs, skip this step entirely. Upload your first CSV through the admin panel and the database file will be created automatically on first write.

---

### Step 6 — Launch the Application

```bash
streamlit run app.py
```

Open your browser and navigate to:

```
http://localhost:8501
```

---

## 📖 Usage Guide

The application has two distinct interfaces that operate in parallel:

### 🔧 Admin Panel (Sidebar)

The sidebar on the left is the **CMS control layer**, accessible to administrators.

#### Uploading New Data

1. In the **"Database Admin"** section, type the name of the SQLite table you want to create or append to (e.g., `employees`, `inventory`, `sales_q3`).
2. Use the **"Upload CSV"** file picker to select your data file.
3. A live 3-row preview of the data will render automatically.
4. Click **"Confirm & Upload"** to write the data to the database.
   - ✅ On success, a confirmation message shows the file name and target table.
   - ⚠️ If the file name was already uploaded to that table, a warning blocks the operation.

#### Removing a Data Batch ("Undo Upload")

1. In the **"Manage Uploads"** section, type the name of the table you want to inspect.
2. A dropdown automatically populates with all distinct source files found in that table.
3. Select the batch you want to remove and click **"Delete"**.
4. All rows from that specific file upload are permanently removed from the table.

---

### 💬 Chat Interface (Main Panel)

The main panel is the **user-facing query layer**.

1. Type any question in plain English into the chat input at the bottom.
2. The agent pre-processes your query (safety check + name translation), then generates and executes a SQL query against the live database.
3. The natural-language answer is returned in the chat window.
4. Use the **"🧹 Clear Chat History"** button in the sidebar to reset the session.

> **Hot-reload behavior:** Because the agent introspects the database schema at query time, **any table uploaded moments ago is immediately queryable** — no restart or re-initialization is needed.

---

## 💬 Example Queries

The following examples assume the default Railway dataset is loaded. The same query patterns apply to any custom dataset.

| Query | What it demonstrates |
|---|---|
| `"How many trains are in the database?"` | Aggregate `COUNT(*)` |
| `"Which train has the longest route by distance?"` | `ORDER BY ... DESC LIMIT 1` pattern |
| `"Find all trains with 'Rajdhani' in their name."` | `LIKE` wildcard text search |
| `"Which trains run from New Delhi to Mumbai?"` | Station name auto-translation + route filtering |
| `"List all stations in the state of Karnataka."` | Column-filtered lookup |
| `"What is the travel duration of train number 12626?"` | Point-lookup by specific ID |

> 🚫 **Blocked queries:** Questions about live train status, ticket prices, platform numbers, fares, or pantry availability are intentionally intercepted before reaching the LLM, as this data is not in the database.

---

## 🔧 Troubleshooting

**`ollama: command not found`**
→ Ollama is not installed or not in your system PATH. Download and install it from [ollama.com](https://ollama.com/download), then restart your terminal.

**`Connection refused` / `Could not connect to Ollama`**
→ The Ollama service is not running. Start it from your system tray or run `ollama serve` in a separate terminal window and leave it running.

**`ModuleNotFoundError`**
→ Your virtual environment is not active, or dependencies were not installed. Run:
```bash
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

**`railway.db not found`**
→ The database file has not been generated yet. Run `python build_db.py` for the railway dataset, or use the Admin panel to upload your first CSV, which will create the database file automatically.

**The agent queries the wrong table or columns**
→ Ensure the CSV headers are clean (no special characters or leading spaces). The LLM uses the column names directly to generate SQL; ambiguous column names may confuse it.

**A new CSV upload is immediately blocked as a duplicate**
→ The `source_file` check is keyed on the exact filename. Rename the file (e.g., `data_v2.csv`) to upload a revised version of a previously uploaded dataset.

---

## 🐳 Docker Deployment *(Alternative)*

A `Dockerfile` and `docker-compose.yml` are included for containerized deployment. Running `docker compose up -d` will spin up the Streamlit app and an Ollama container, and pull the `mistral` model automatically.

```bash
docker compose up -d
```

---

## 📄 License

The original Indian Railway dataset is sourced from [datameet/railways](https://github.com/datameet/railways) and is used under its respective open data license.
