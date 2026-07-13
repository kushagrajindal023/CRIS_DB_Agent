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

# --- 1. BULLETPROOF AUTO-INGESTION (With Nested Data Fix) ---
# --- 1. BULLETPROOF AUTO-INGESTION ---
def auto_ingest_json():
    """Safely initializes DB from JSON files, sanitizes nested data, and unpacks GeoJSON wrappers."""
    if not os.path.exists(db_filename):
        open(db_filename, 'a').close()

    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    tables_added = False
    
    for table_name in ['trains', 'stations']:
        json_file = f"{table_name}.json"
        
        # Check if table exists AND has rows
        table_exists = False
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            if cursor.fetchone()[0] > 0:
                table_exists = True
        except sqlite3.OperationalError:
            pass 
            
        if not table_exists:
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                    
                    # --- THE FIX: Unpack FeatureCollection wrappers ---
                    if isinstance(data, dict) and 'features' in data and isinstance(data['features'], list):
                        # This extracts the actual list of trains and flattens nested properties
                        df = pd.json_normalize(data['features'])
                        # Clean up GeoJSON column names (e.g., changes 'properties.train_name' to 'train_name')
                        df.columns = [col.replace('properties.', '') for col in df.columns]
                        
                    elif table_name == 'stations' and isinstance(data, dict) and all(not isinstance(v, (list, dict)) for v in data.values()):
                        df = pd.DataFrame(list(data.items()), columns=['station_name', 'station_code'])
                    elif isinstance(data, dict):
                        if all(not isinstance(v, (list, dict)) for v in data.values()):
                            df = pd.DataFrame([data])
                        else:
                            df = pd.DataFrame.from_dict(data)
                    else:
                        df = pd.DataFrame(data)
                        
                    # SANITIZE: Convert any nested Python lists/dicts into JSON strings
                    for col in df.columns:
                        df[col] = df[col].apply(
                            lambda x: json.dumps(x) if isinstance(x, (list, dict)) else x
                        )
                        
                    # Write clean data to database
                    df.to_sql(table_name, conn, if_exists='replace', index=False)
                    tables_added = True
                except Exception as e:
                    st.sidebar.error(f"Failed to load {json_file}: {e}")
    conn.close()
    
    if tables_added:
        st.cache_resource.clear()
auto_ingest_json()

# --- 2. Load the Dictionary ---
@st.cache_data 
def load_station_map():
    try:
        with open('stations.json', 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return {} 
            return data
    except (FileNotFoundError, json.JSONDecodeError):
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
    
    try:
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        if cursor.fetchone()[0] == 0:
            conn.close()
            return None
    except:
        conn.close()
        return None
        
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    
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
    
    # --- LIVE DB STATS ---
    st.subheader("📊 Live Database Stats")
    try:
        monitor_conn = sqlite3.connect(db_filename)
        t_count = pd.read_sql("SELECT COUNT(*) as c FROM trains", monitor_conn)['c'].iloc[0]
        s_count = pd.read_sql("SELECT COUNT(*) as c FROM stations", monitor_conn)['c'].iloc[0]
        monitor_conn.close()
        st.write(f"🔹 **Trains Table:** {t_count} rows loaded")
        st.write(f"🔹 **Stations Table:** {s_count} rows loaded")
    except Exception:
        st.write("❌ Tables not fully created yet.")
    st.markdown("---")
    
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant."}]
        st.rerun()
        
    st.markdown("---")
    
    st.subheader("📁 Database Admin")
    target_table = st.text_input("Enter Table Name:", value="trains")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        file_name = uploaded_file.name
        df['source_file'] = file_name
        st.dataframe(df.head(3)) 
        
        if st.button("Confirm & Upload", use_container_width=True):
            conn = sqlite3.connect(db_filename)
            
            # Duplicate Firewall
            file_exists = False
            try:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {target_table} WHERE source_file = ?", (file_name,))
                if cursor.fetchone()[0] > 0:
                    file_exists = True
            except sqlite3.OperationalError:
                pass 
                
            if file_exists:
                st.warning(f"⚠️ Stop! The file '{file_name}' has already been uploaded to '{target_table}'.")
                conn.close()
            else:
                try:
                    conn.execute(f"ALTER TABLE {target_table} ADD COLUMN source_file TEXT")
                except sqlite3.OperationalError:
                    pass 
                    
                df.to_sql(target_table, conn, if_exists='append', index=False)
                conn.close()
                
                st.cache_resource.clear()
                st.success(f"✅ Data from '{file_name}' uploaded successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Manage Uploads")
    manage_table = st.text_input("Table to manage:", value="trains", key="manage")

    conn = sqlite3.connect(db_filename)
    try:
        files = pd.read_sql(f"SELECT DISTINCT source_file FROM {manage_table} WHERE source_file IS NOT NULL", conn)
        files_in_db = files['source_file'].tolist()
        if files_in_db:
            file_to_del = st.selectbox("Select file to remove:", files_in_db)
            if st.button("Delete Data"):
                conn.execute(f"DELETE FROM {manage_table} WHERE source_file = ?", (file_to_del,))
                
                # Auto-Drop Empty Table
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {manage_table}")
                if cursor.fetchone()[0] == 0:
                    conn.execute(f"DROP TABLE {manage_table}")
                    
                conn.commit()
                st.cache_resource.clear()
                st.success(f"🗑️ '{file_to_del}' wiped from '{manage_table}'!")
                st.rerun()
        else: 
            st.info("No tracked files found.")
    except Exception: 
        st.info("No tracked files found.")
    finally:
        conn.close()

# --- 6. App Header & Chat ---
st.title("🚆 CRIS Database Agent")
vector_store = initialize_database_knowledge()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

prompt = st.chat_input("Message CRIS Agent...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    
    with st.chat_message("assistant"):
        if vector_store:
            with st.status("Querying..."):
                # 1. Skip the text lowercasing, pass the raw prompt to preserve intent
                match = vector_store.similarity_search(prompt, k=1)[0].page_content
                
                # 2. Instruct the LLM to use LIKE for case-insensitive matching
                ai_instructions = f"Write SQL for: '{prompt}' using this schema: {match}. IMPORTANT: Always use the 'LIKE' operator with '%' wildcards instead of '=' for text filtering to handle case insensitivity. Return ONLY valid SQL code."
                
                sql = llm.invoke(ai_instructions).content.replace("```sql", "").replace("```", "").strip()
                
                try:
                    conn = sqlite3.connect(db_filename)
                    df = pd.read_sql_query(sql, conn)
                    conn.close()
                    
                    st.dataframe(df)
                    
                    # 3. Add a debug expander so you can inspect the generated SQL!
                    with st.expander("🔍 See Generated SQL"):
                        st.code(sql, language="sql")
                        
                    st.session_state.messages.append({"role": "assistant", "content": f"Here is the data you requested!"})
                except Exception as e: 
                    st.error(f"SQL Error: {e}")
        else: 
            st.warning("Database not initialized. Please check your data files.")