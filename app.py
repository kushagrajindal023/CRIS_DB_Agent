import os
import json
import pandas as pd
import sqlite3
import streamlit as st

# --- NEW RAG IMPORTS ---
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
# Using the secrets.toml file we discussed
os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

embedder = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
db_filename = "railway.db"

# --- 1. Load the Dictionary ---
@st.cache_data 
def load_station_map():
    try:
        with open('stations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

STATION_LOOKUP = load_station_map()

# --- 2. Clean Input ---
def secure_clean_input(user_question):
    lowered_question = user_question.lower()
    for city_name, station_code in STATION_LOOKUP.items():
        if city_name in lowered_question:
            lowered_question = lowered_question.replace(city_name, station_code)
    return lowered_question

# --- 3. RAG STEP 1: AUTOMATED LIVE SCHEMA INGESTION ---
@st.cache_resource
def initialize_database_knowledge():
    """Calculates the embedded vectors of the database schemas."""
    if not os.path.exists(db_filename):
        return None
        
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    if not tables:
        conn.close()
        return None
        
    live_metadata = {}
    for table_name in tables:
        if table_name.startswith("sqlite_"): continue
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [col[1] for col in cursor.fetchall()]
        
        auto_prompt = f"Write a concise sentence describing a table named '{table_name}' with columns: {', '.join(columns)}. Return ONLY the sentence."
        ai_description = llm.invoke(auto_prompt).content.strip()
        live_metadata[table_name] = {"columns": columns, "description": ai_description}
    conn.close()
    
    schema_descriptions = []
    for table, info in live_metadata.items():
        schema_descriptions.append(f"Table: {table}. Columns: {', '.join(info['columns'])}. Description: {info['description']}")
        
    vector_store = Chroma.from_texts(texts=schema_descriptions, embedding=embedder)
    return vector_store

# --- Sidebar Controls & Admin ---
with st.sidebar:
    st.title("⚙️ Agent Controls")
    st.markdown("Use this panel to manage the chat session.")
    
    # 1. Clear Chat Button
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant. Ask me about your uploaded data."}]
        st.rerun()
        
    st.markdown("---")
    
    # --- 2. Database Admin Uploader ---
    st.subheader("📁 Database Admin")
    st.markdown("Upload new data (CSV format) directly to the backend.")
    
    target_table = st.text_input("Enter Database Table Name (e.g., trains, employees):", value="trains")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        file_name = uploaded_file.name
        df['source_file'] = file_name
       
        st.write("Data Preview:")
        st.dataframe(df.head(3)) 
        
        if st.button("Confirm & Upload", use_container_width=True):
            try:
                conn = sqlite3.connect(db_filename)
                
                # SECURITY CHECK: Duplicate Firewall
                file_exists = False
                try:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {target_table} WHERE source_file = ?", (file_name,))
                    if cursor.fetchone()[0] > 0:
                        file_exists = True
                except sqlite3.OperationalError:
                    pass 

                if file_exists:
                    st.warning(f"⚠️ Stop! The file '{file_name}' has already been uploaded to the '{target_table}' table.")
                    conn.close()
                else:
                    try:
                        conn.execute(f"ALTER TABLE {target_table} ADD COLUMN source_file TEXT")
                    except sqlite3.OperationalError:
                        pass 
                        
                    df.to_sql(target_table, conn, if_exists='append', index=False)
                    conn.close()
                    st.success(f"✅ Data from '{file_name}' uploaded successfully into '{target_table}'!")
                    
                    # 🔴 RAG TRIGGER: Clear cache to calculate embedded vectors of the new file automatically!
                    st.cache_resource.clear()
            except Exception as e:
                st.error(f"❌ Error uploading: {e}") 

    # --- 3. Data Management (The Undo Button) ---
    st.markdown("---")
    st.subheader("🗑️ Manage Uploads")
    st.markdown("Remove an entire batch of data based on the file name.")

    manage_table = st.text_input("Table to manage:", value="trains", key="manage_table_input")

    try:
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT DISTINCT source_file FROM {manage_table} WHERE source_file IS NOT NULL")
            files_in_db = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            files_in_db = []
        conn.close()
        
        if files_in_db:
            file_to_delete = st.selectbox("Select a file to remove:", files_in_db)
            
            if st.button(f"Delete '{file_to_delete}' Data", type="primary"):
                conn = sqlite3.connect(db_filename)
                conn.execute(f"DELETE FROM {manage_table} WHERE source_file = ?", (file_to_delete,))
                
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {manage_table}")
                if cursor.fetchone()[0] == 0:
                    conn.execute(f"DROP TABLE {manage_table}")
                    
                conn.commit()
                conn.close()
                st.success(f"🗑️ '{file_to_delete}' wiped from '{manage_table}'!")
                
                # 🔴 RAG TRIGGER: Clear cache to update embedded vectors after deletion!
                st.cache_resource.clear()
                st.rerun() 
        else:
            st.info(f"No tracked file uploads found in '{manage_table}'.")
            
    except Exception as e:
        st.error(f"Database error: {e}")

# --- App Header ---
st.title("🚆 CRIS Database Agent")
st.markdown("---") 

# Load the vector store automatically on launch
vector_store = None
if os.path.exists(db_filename):
    with st.spinner("🔄 Initializing AI and calculating embedded vectors..."):
        vector_store = initialize_database_knowledge()
else:
    st.info("👈 Please use the Database Admin panel to upload your first CSV file.")

# --- 4. Chat Interface Memory ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "type": "text", "content": "Hello! I am your CRIS database assistant. Ask me about your uploaded data."}]

for message in st.session_state.messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🚆"
    with st.chat_message(message["role"], avatar=avatar):
        if message["type"] == "text":
            st.markdown(message["content"])
        elif message["type"] == "dataframe":
            st.dataframe(message["content"], use_container_width=True)

# --- 5. The Main Chat Loop (RAG Execution) ---
prompt = st.chat_input("Message CRIS Agent...", disabled=(vector_store is None))
if prompt:
    
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})
    st.chat_message("user", avatar="🧑‍💻").markdown(prompt)

    with st.chat_message("assistant", avatar="🚆"):
        with st.status("Searching database...") as status:
            cleaned_query = secure_clean_input(prompt)
            
            try:
                # STEP A: RAG RETRIEVAL 
                status.update(label="🕵️ Finding correct table schema...")
                best_matches = vector_store.similarity_search(cleaned_query, k=1)
                retrieved_table_info = best_matches[0].page_content
                
                # STEP B: RAG GENERATION (Writing the SQL)
                status.update(label="🧠 Writing specific SQL query...")
                dynamic_prompt = f"""
                You are a precise data analyst. 
                Translate this question into a SQLite query: "{cleaned_query}"
                
                Use ONLY this database schema context:
                {retrieved_table_info}
                
                Instructions:
                1. Write standard SQL. Do NOT select the 'source_file' tracking column.
                2. Return ONLY the raw, executable SQL query string. 
                3. Do not include markdown formatting or conversational text.
                """
                generated_sql = llm.invoke(dynamic_prompt).content.strip()
                generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()
                
                # STEP C: RAG EXECUTION (Pandas Dataframe)
                status.update(label="⚡ Fetching data from SQLite...")
                conn = sqlite3.connect(db_filename)
                result_df = pd.read_sql_query(generated_sql, conn)
                conn.close()
                
                status.update(label="✅ Data retrieved successfully!", state="complete")
                
            except Exception as e:
                status.update(label="❌ Encountered an error", state="error")
                st.error(f"Technical error: {e}")
                result_df = None

        # Display final results to the user
        if result_df is not None:
            if result_df.empty:
                empty_msg = "The query ran successfully, but no matching records were found."
                st.markdown(empty_msg)
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": empty_msg})
            else:
                st.dataframe(result_df, use_container_width=True)
                # Save the table to chat history so it doesn't disappear
                st.session_state.messages.append({"role": "assistant", "type": "dataframe", "content": result_df})