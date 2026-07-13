import os
import json
import pandas as pd
import sqlite3
import streamlit as st

# --- RAG IMPORTS ---
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# --- Page Configuration ---
st.set_page_config(page_title="CRIS AI Assistant", page_icon="🚆", layout="centered", initial_sidebar_state="expanded")

# --- UI Upgrades: Hide Streamlit Menus & Watermarks ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .block-container {
                padding-top: 2rem;
                padding-bottom: 0rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- SECURITY & KEYS CONFIGURATION ---
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

embedder = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
db_filename = "railway.db"

# --- 1. NEW PART: AUTO-INGESTION ---
@st.cache_resource
def auto_ingest_json():
    """Initializes DB from JSON if tables are missing."""
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    # Check if tables 'trains' or 'stations' already exist in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('trains', 'stations');")
    tables_found = [row[0] for row in cursor.fetchall()]
    
    # Only ingest if the table is not already found
    for json_file in ['trains.json', 'stations.json']:
        table_name = json_file.replace('.json', '')
        if table_name not in tables_found and os.path.exists(json_file):
            with open(json_file, 'r') as f:
                pd.DataFrame(json.load(f)).to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()

# Run the ingestion immediately on start
auto_ingest_json()

# --- 2. Load the Dictionary ---
@st.cache_data 
def load_station_map():
    try:
        with open('stations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

STATION_LOOKUP = load_station_map()

# --- 3. Clean Input ---
def secure_clean_input(user_question):
    lowered_question = user_question.lower()
    for city_name, station_code in STATION_LOOKUP.items():
        if city_name in lowered_question:
            lowered_question = lowered_question.replace(city_name, station_code)
    return lowered_question

# --- 4. RAG STEP: AUTOMATED LIVE SCHEMA INGESTION ---
@st.cache_resource
def initialize_database_knowledge():
    """Calculates the embedded vectors of the database schemas."""
    if not os.path.exists(db_filename):
        return None
        
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
    
    if not tables:
        conn.close()
        return None
        
    schema_descriptions = []
    for table_name in tables:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in cursor.fetchall()]
        schema_descriptions.append(f"Table: {table_name}. Columns: {', '.join(columns)}.")
        
    conn.close()
    return Chroma.from_texts(texts=schema_descriptions, embedding=embedder)

# --- 5. Sidebar Controls & Admin ---
with st.sidebar:
    st.title("⚙️ Agent Controls")
    
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant."}]
        st.rerun()
        
    st.markdown("---")
    
    st.subheader("📁 Database Admin")
    target_table = st.text_input("Enter Table Name:", value="trains")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df['source_file'] = uploaded_file.name
        st.dataframe(df.head(3)) 
        
        if st.button("Confirm & Upload", use_container_width=True):
            conn = sqlite3.connect(db_filename)
            df.to_sql(target_table, conn, if_exists='append', index=False)
            conn.close()
            st.cache_resource.clear()
            st.success("Uploaded!")
            st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Manage Uploads")
    manage_table = st.text_input("Table to manage:", value="trains")

    conn = sqlite3.connect(db_filename)
    try:
        files = pd.read_sql(f"SELECT DISTINCT source_file FROM {manage_table} WHERE source_file IS NOT NULL", conn)
        files_in_db = files['source_file'].tolist()
        if files_in_db:
            file_to_del = st.selectbox("Select file to remove:", files_in_db)
            if st.button("Delete Data"):
                conn.execute(f"DELETE FROM {manage_table} WHERE source_file = ?", (file_to_del,))
                conn.commit()
                st.cache_resource.clear()
                st.rerun()
        else: st.info("No tracked files found.")
    except: st.info("No tracked files found.")
    conn.close()

# --- 6. App Header & Chat ---
st.title("🚆 CRIS Database Agent")
vector_store = initialize_database_knowledge()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

# Main Chat Input (No longer disabled)
prompt = st.chat_input("Message CRIS Agent...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        if vector_store:
            with st.status("Querying..."):
                cleaned = secure_clean_input(prompt)
                match = vector_store.similarity_search(cleaned, k=1)[0].page_content
                sql = llm.invoke(f"Write SQL for: {cleaned} using: {match}. Return ONLY SQL.").content.replace("```sql", "").replace("```", "").strip()
                try:
                    conn = sqlite3.connect(db_filename)
                    df = pd.read_sql_query(sql, conn)
                    conn.close()
                    st.dataframe(df)
                    st.session_state.messages.append({"role": "assistant", "content": f"Query: {sql}"})
                except Exception as e: st.error(f"Error: {e}")
        else: st.warning("Database not initialized.")