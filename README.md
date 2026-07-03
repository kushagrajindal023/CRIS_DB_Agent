# 🚆 CRIS Database Agent

An AI-powered assistant for querying Indian Railway data. Ask questions in plain English and get answers from a real SQLite database of trains and stations — powered by a local LLM (Mistral via Ollama) and LangChain's Text-to-SQL pipeline.

---

## 📋 Features

- 🤖 Natural language querying using a local Mistral LLM
- 🗄️ SQLite database with thousands of real Indian Railway trains and stations
- 🔒 Built-in safety firewall to block out-of-scope queries
- 🧠 Station name-to-code auto-translation (e.g. "Delhi" → `NDLS`)
- 💬 Chat interface with memory (via Streamlit)
- 🖥️ CLI mode available (`railway_agent_free.py`)

---

## 🛠️ Prerequisites

Before you begin, make sure you have the following installed on your machine:

| Requirement | Version | Install Link |
|---|---|---|
| Python | 3.9 or above | [python.org](https://www.python.org/downloads/) |
| Ollama | Latest | [ollama.com](https://ollama.com/download) |

---

## 🚀 Setup & Run (Without Docker)

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/CRIS_db_agent.git
cd CRIS_db_agent
```

---

### Step 2 — Create a Virtual Environment

```bash
# Create the virtual environment
python -m venv venv

# Activate it:
# On Windows:
venv\Scripts\activate

# On macOS / Linux:
source venv/bin/activate
```

---

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Pull the Mistral Model via Ollama

Make sure the **Ollama** application is running, then pull the required model:

```bash
ollama pull mistral
```

> ⏳ This is a one-time download of ~4.4 GB. Subsequent runs will be instant.

To verify the model is ready:
```bash
ollama list
```
You should see `mistral:latest` in the output.

---

### Step 5 — Build the Railway Database

This downloads the raw data and builds your local `railway.db` SQLite database:

```bash
python build_db.py
```

Expected output:
```
1. Downloading raw JSON data from GitHub...
2. Loading data into memory...
3. Building SQLite database schema...
4. Inserting data into tables (this might take a few seconds)...

Success! Database is built and ready.
Total Trains Inserted: XXXXX
Total Stations Inserted: XXXXX
```

> ℹ️ This only needs to be run **once**. The generated `railway.db` file is local and will be reused on future runs.

---

### Step 6 — Run the App

```bash
streamlit run app.py
```

Then open your browser and go to:

```
http://localhost:8501
```

---

## 💬 Example Questions to Ask

| Question | What it tests |
|---|---|
| `"How many trains are in the database?"` | Aggregate count |
| `"Which train has the longest route by distance?"` | MAX with ordering |
| `"Find all trains with 'Rajdhani' in their name."` | LIKE text search |
| `"Which trains run from NDLS to BCT?"` | Route filtering |
| `"List all stations in the state of Karnataka."` | Station lookup |
| `"What is the travel duration of train number 12626?"` | Specific train query |

> 🚫 **Blocked queries**: Questions about live status, ticket prices, fares, platforms, or pantry are intentionally blocked as this data is not in the database.

---

## 🖥️ CLI Mode (Optional)

Prefer the terminal? Run the command-line version instead:

```bash
python railway_agent_free.py
```

Type your questions at the prompt and type `quit` or `exit` to stop.

---

## 📁 Project Structure

```
CRIS_db_agent/
│
├── app.py                  # Main Streamlit web application
├── railway_agent_free.py   # Command-line interface version
├── build_db.py             # Script to download data and build railway.db
├── build_stations.py       # Script to build stations.json lookup map
├── stations.json           # Station name → code lookup map (committed)
├── requirements.txt        # Python dependencies
│
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose multi-service setup
├── .dockerignore           # Files excluded from Docker build context
├── .gitignore              # Files excluded from Git version control
│
└── .streamlit/
    └── config.toml         # Streamlit UI theme configuration
```

> **Note**: `trains.json` (14 MB) and `railway.db` (1.1 MB) are excluded from the repository via `.gitignore`. They are generated locally by running `build_db.py`.

---

## 🐳 Docker Deployment (Alternative)

If you prefer Docker, see the **[docker-compose.yml](docker-compose.yml)** file. Running `docker compose up -d` will automatically spin up the Streamlit app and an Ollama container, and pull the `mistral` model.

---

## 🔧 Troubleshooting

**`ollama: command not found`**
→ Make sure Ollama is installed and running. Download it from [ollama.com](https://ollama.com/download).

**`Connection refused` error in the app**
→ Ollama is not running. Start it from your system tray or run `ollama serve` in a terminal.

**`ModuleNotFoundError`**
→ Make sure your virtual environment is activated and `pip install -r requirements.txt` was run.

**`railway.db not found`**
→ Run `python build_db.py` to generate the database file.

---

## 📄 License

This project uses open railway data from [datameet/railways](https://github.com/datameet/railways).
