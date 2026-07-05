import streamlit as st
import json
import pandas as pd
import sqlite3
from langchain_community.utilities import SQLDatabase
from langchain_community.llms import Ollama
from langchain_experimental.sql import SQLDatabaseChain
from langchain_core.prompts import PromptTemplate

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

# --- Sidebar Controls & Admin ---
with st.sidebar:
    st.title("⚙️ Agent Controls")
    st.markdown("Use this panel to manage the chat session.")
    
    # 1. Clear Chat Button
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant. Ask me about train routes, distances, and durations."}]
        st.rerun()
        
    st.markdown("---")
    
    # --- 2. Database Admin Uploader ---
    st.subheader("📁 Database Admin")
    st.markdown("Upload new data (CSV format) directly to the backend.")
    
    # NEW: Dynamic Table Input
    target_table = st.text_input("Enter Database Table Name (e.g., trains, employees):", value="trains")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Stamp every row with the file name for tracking
        file_name = uploaded_file.name
        df['source_file'] = file_name
       
        st.write("Data Preview:")
        st.dataframe(df.head(3)) 
        
        if st.button("Confirm & Upload", use_container_width=True):
            try:
                conn = sqlite3.connect('railway.db')
                
                # --- NEW SECURITY CHECK ---
                file_exists = False
                try:
                    cursor = conn.cursor()
                    # Ask the database if this exact file name is already inside this exact table
                    cursor.execute(f"SELECT COUNT(*) FROM {target_table} WHERE source_file = ?", (file_name,))
                    if cursor.fetchone()[0] > 0:
                        file_exists = True
                except sqlite3.OperationalError:
                    pass # The table hasn't been created yet, which means the file definitely isn't there!
                
                # --- UPLOAD LOGIC ---
                if file_exists:
                    st.warning(f"⚠️ Stop! The file '{file_name}' has already been uploaded to the '{target_table}' table.")
                    conn.close()
                else:
                    # Dynamically alter whatever table name was typed
                    try:
                        conn.execute(f"ALTER TABLE {target_table} ADD COLUMN source_file TEXT")
                    except sqlite3.OperationalError:
                        pass 
                        
                    # Upload to the dynamically named table
                    df.to_sql(target_table, conn, if_exists='append', index=False)
                    conn.close()
                    st.success(f"✅ Data from '{file_name}' uploaded successfully into '{target_table}'!")
                    
            except Exception as e:
                st.error(f"❌ Error uploading: {e}") 
                    
                # NEW: Upload to the dynamically named table
                df.to_sql(target_table, conn, if_exists='append', index=False)
                conn.close()
                st.success(f"✅ Data from '{file_name}' uploaded successfully into '{target_table}'!")
            except Exception as e:
                st.error(f"❌ Error uploading: {e}")

    # --- 3. Data Management (The Undo Button) ---
    st.markdown("---")
    st.subheader("🗑️ Manage Uploads")
    st.markdown("Remove an entire batch of data based on the file name.")

    # NEW: Tell the undo button which table to look at
    manage_table = st.text_input("Table to manage:", value="trains", key="manage_table_input")

    try:
        conn = sqlite3.connect('railway.db')
        cursor = conn.cursor()
        
        # NEW: Find files only in the dynamically selected table
        try:
            cursor.execute(f"SELECT DISTINCT source_file FROM {manage_table} WHERE source_file IS NOT NULL")
            files_in_db = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            files_in_db = []
            
        conn.close()
        
        if files_in_db:
            file_to_delete = st.selectbox("Select a file to remove:", files_in_db)
            
            if st.button(f"Delete '{file_to_delete}' Data", type="primary"):
                conn = sqlite3.connect('railway.db')
                # NEW: Delete from the dynamically selected table
                conn.execute(f"DELETE FROM {manage_table} WHERE source_file = ?", (file_to_delete,))
                conn.commit()
                conn.close()
                st.success(f"🗑️ '{file_to_delete}' wiped from '{manage_table}'!")
                st.rerun() 
        else:
            st.info(f"No tracked file uploads found in '{manage_table}'.")
            
    except Exception as e:
        st.error(f"Database error: {e}")

# --- App Header ---
st.title("🚆 CRIS Database Agent")
st.markdown("---") 

# --- 1. Load the Dictionary ---
@st.cache_data 
def load_station_map():
    # Wrap in try/except just in case the JSON file is missing during a cold boot
    try:
        with open('stations.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

STATION_LOOKUP = load_station_map()

# --- 2. The Safety Firewall ---
def secure_clean_input(user_question):
    lowered_question = user_question.lower()
    
    forbidden_words = ["platform", "ticket price", "live status", "fare", "pantry"]
    if any(word in lowered_question for word in forbidden_words):
        return "BLOCKED"
        
    for city_name, station_code in STATION_LOOKUP.items():
        if city_name in lowered_question:
            lowered_question = lowered_question.replace(city_name, station_code)
            
    return lowered_question

# --- 3. Initialize the AI Agent ---
@st.cache_resource 
def get_agent():
    # NEW: Removed include_tables so LangChain can see any new table you upload [cite: 12]
    db = SQLDatabase.from_uri('sqlite:///railway.db')
    
    llm = Ollama(model='mistral', base_url='http://localhost:11434', temperature=0)    
    
    # NEW: Generalized Template for multi-table queries
    _DEFAULT_TEMPLATE = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.

    STRICT SQL RULES:
    1. Carefully analyze the available tables in {table_info} to determine which table contains the data needed to answer the question.
    2. ONLY use the columns explicitly listed in the schema for the chosen table. 
    3. To find the highest, longest, or maximum, prefer using 'ORDER BY column DESC LIMIT 1'.
    4. If the user asks for data that does not exist in ANY table, do not write a SQL query. Instead, return: "I cannot answer this as that specific data is not available."

    Use the following format:
    Question: Question here
    SQLQuery: SQL Query to run
    SQLResult: Result of the SQLQuery
    Answer: Final answer here

    Only use the following tables:
    {table_info}

    Question: {input}"""

    PROMPT = PromptTemplate(input_variables=["input", "table_info", "dialect"], template=_DEFAULT_TEMPLATE)
    
    return SQLDatabaseChain.from_llm(llm=llm, db=db, prompt=PROMPT, verbose=True, use_query_checker=False)

agent = get_agent()

# --- 4. Chat Interface Memory ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your CRIS database assistant. Ask me about train routes, distances, and durations."}]

for message in st.session_state.messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🚆"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# --- 5. The Main Chat Loop ---
prompt = st.chat_input("Message CRIS Agent...")
if prompt:
    
    st.chat_message("user", avatar="🧑‍💻").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar="🚆"):
        with st.spinner("Searching database..."):
            
            cleaned_query = secure_clean_input(prompt)
            
            if cleaned_query == "BLOCKED":
                response_text = "I cannot answer this as that specific data (like platforms or prices) is not available in the database."
            else:
                try:
                    result = agent.invoke(cleaned_query)
                    response_text = result["result"]
                except Exception as e:
                    # This will print the literal python error into your chat UI
                    response_text = f"I encountered a technical error: {e}"
            
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})