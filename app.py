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
    
    # 2. Database Admin Uploader
    st.subheader("📁 Database Admin")
    st.markdown("Upload new train data (CSV format) directly to the backend.")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Show a quick preview
        st.write("Data Preview:")
        st.dataframe(df.head(3)) 
        
        # Add confirmation button to prevent accidental clicks
        if st.button("Confirm & Upload", use_container_width=True):
            try:
                # Connect to the SQLite DB and append the CSV data
                conn = sqlite3.connect('railway.db')
                df.to_sql('trains', conn, if_exists='append', index=False)
                conn.close()
                st.success("✅ Database updated successfully! The AI can now query this new data.")
            except Exception as e:
                st.error(f"❌ Error uploading: {e}")

# --- App Header ---
st.title("🚆 CRIS Database Agent")
st.markdown("---") 

# --- 1. Load the Dictionary ---
@st.cache_data 
def load_station_map():
    with open('stations.json', 'r') as f:
        return json.load(f)

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
    db = SQLDatabase.from_uri('sqlite:///railway.db', include_tables=['trains', 'stations'])
    
    # Using localhost because we are running this directly on your machine now
    llm = Ollama(model='mistral', base_url='http://localhost:11434', temperature=0)    
    
    _DEFAULT_TEMPLATE = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.

    STRICT SQL RULES:
    1. If the question asks "Which train", "What train", or asks for identities, your SQLQuery MUST select the train name column.
    2. To find the highest, longest, or maximum, prefer using 'ORDER BY column DESC LIMIT 1'.
    3. Always use the LIKE operator with wildcards on the train name column for specific trains (e.g., WHERE name LIKE '%Rajdhani%').
    4. ONLY use the columns explicitly listed in the schema below. If the user asks for data that does not exist, do not write a SQL query. Instead, return: "I cannot answer this as that specific data is not available."

    Use the following format:
    Question: Question here
    SQLQuery: SQL Query to run
    SQLResult: Result of the SQLQuery
    Answer: Final answer here

    Only use the following tables:
    {table_info}

    Question: {input}"""

    # These are now perfectly aligned with the rest of the function:
    PROMPT = PromptTemplate(input_variables=["input", "table_info", "dialect"], template=_DEFAULT_TEMPLATE)
    
    return SQLDatabaseChain.from_llm(llm=llm, db=db, prompt=PROMPT, verbose=True, use_query_checker=False)

# This line stays against the left margin, outside the function:
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
                    response_text = "I encountered a technical error while querying the database."
            
            st.markdown(response_text)
            st.session_state.messages.append({"role": "assistant", "content": response_text})