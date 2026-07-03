from langchain_community.utilities import SQLDatabase
from langchain_community.llms import Ollama
from langchain_experimental.sql import SQLDatabaseChain
from langchain_core.prompts import PromptTemplate
import json
import os

# Load the automatically generated dictionary
with open('stations.json', 'r') as f:
    STATION_LOOKUP = json.load(f)

def secure_clean_input(user_question):
    lowered_question = user_question.lower()
    
    # 1. Block unsafe topics completely
    forbidden_words = ["platform", "ticket price", "live status", "fare"]
    if any(word in lowered_question for word in forbidden_words):
        return "BLOCKED"
        
    # 2. Swap names with exact codes from your new JSON file
    for city_name, station_code in STATION_LOOKUP.items():
        if city_name in lowered_question:
            lowered_question = lowered_question.replace(city_name, station_code)
            
    return lowered_question

print("1. Connecting to the Railway Database...")
db = SQLDatabase.from_uri(
    'sqlite:///railway.db',
    include_tables=['trains', 'stations'],
    sample_rows_in_table_info=2
)

print("2. Waking up the local AI Model...")
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = Ollama(base_url=ollama_base_url, model='mistral', temperature=0)

print("3. Assembling the Text-to-SQL Agent...")

# --- NEW: The Custom Prompt Template ---
# This forces Mistral to use the exact structure LangChain expects.
# The Custom Prompt Template with strict schema guardrails
_DEFAULT_TEMPLATE = """Given an input question, first create a syntactically correct {dialect} query to run, then look at the results of the query and return the answer.

STRICT SQL RULES:
1. If the question asks "Which train", "What train", or asks for identities, your SQLQuery MUST select the train name column along with any values (e.g., SELECT name, distance...). Never just select a single numeric value if a specific entity is being asked for.
2. To find the highest, longest, or maximum of something while retrieving names, prefer using 'ORDER BY column DESC LIMIT 1' instead of using 'SELECT MAX()'.
3. If the question mentions a specific category, brand, or type of train (such as 'Rajdhani', 'Shatabdi', 'Garib Rath', 'Duronto'), do NOT invent extra columns like 'zone' or 'type'. Instead, always use the LIKE operator with wildcards on the train name column (e.g., WHERE name LIKE '%Rajdhani%').
4. ONLY use the columns explicitly listed in the schema below. Do NOT invent or assume columns (like 'platform', 'status', 'ticket price'). If the user asks for data that does not exist in the schema, do not write a SQL query. Instead, directly return this Answer: "I cannot answer this as that specific data is not available in the database."

Use the following format:

Question: Question here
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer here

Only use the following tables:
{table_info}

Question: {input}"""

PROMPT = PromptTemplate(
    input_variables=["input", "table_info", "dialect"], template=_DEFAULT_TEMPLATE
)
# ---------------------------------------

# We pass our custom PROMPT into the chain here
agent = SQLDatabaseChain.from_llm(
    llm=llm, 
    db=db, 
    prompt=PROMPT,      # <-- Injecting the new rules
    verbose=True, 
    use_query_checker=False # <-- Keep this False so it doesn't try to double-check itself
)

print('\n🚂 CRIS Railway Agent is Online! (Type "quit" to exit)')
print('-' * 50)

while True:
    user_input = input('\nYou: ').strip()
    
    if user_input.lower() in ['quit', 'exit']: 
        print("Shutting down agent. Goodbye!")
        break
    if not user_input: 
        continue
        
    # --- The Security Checkpoint ---
    cleaned_query = secure_clean_input(user_input)
    
    if cleaned_query == "BLOCKED":
        print("\nAgent: I cannot answer this as that specific data is not available in the database.")
        continue
        
    try:
        # Pass the safely filtered query to the agent instead of the raw input
        response = agent.invoke(cleaned_query)
        print(f'\nAgent: {response["result"]}')
    except Exception as e:
        print(f'\nAgent: I encountered a technical error: {e}')