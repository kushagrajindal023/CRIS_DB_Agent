import os
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# 1. SET UP YOUR FREE CLOUD KEYS
os.environ["GROQ_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

# 2. INITIALIZE THE LIBRARIAN (Google's Free Cloud Embeddings)
print("📥 Connecting to Google API for embeddings...")
embedder = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# 3. INITIALIZE THE PROFESSOR (Groq's Free Cloud LLM)
print("🧠 Connecting to Groq API...")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)

# 4. PREPARE THE DATA (Your database schemas)
database_schemas = [
    "Table: hr_payroll. Columns: employee_name, salary, shift_timing. Use this for questions about money, pay, or staff.",
    "Table: locomotives. Columns: engine_id, mileage, status, zone. Use this for questions about trains, vehicles, driving distance, or broken engines.",
    "Table: cafeteria_menu. Columns: food_item, price, calories. Use this for questions about lunch, snacks, or eating."
]

print("📚 Building the Vector Database in Cloud Memory...")
# This sends the text to Google to turn it into math coordinates,
# then saves those coordinates in a fast, temporary database.
vector_store = Chroma.from_texts(
    texts=database_schemas, 
    embedding=embedder
)
print("✅ Database ready!\n")

# 5. TEST THE PIPELINE
user_question = "Which engines have driven the most miles?"
print(f"👤 User asks: '{user_question}'")

print("\n--- RUNNING THE RAG PIPELINE ---")

# Part A: Retrieval (The Search)
best_matches = vector_store.similarity_search(user_question, k=1)
retrieved_table_info = best_matches[0].page_content
print(f"🕵️ Librarian found the relevant schema:\n   -> {retrieved_table_info}")

# Part B: Generation (Creating the context-aware prompt)
dynamic_prompt = f"""
You are an expert SQL assistant. 
The user is asking a question: "{user_question}"

Here is the ONLY table you should use to write the SQL query:
{retrieved_table_info}

What SQL table and column should I use to answer this?
"""

# Part C: Execution (Getting the answer from Groq)
print("\n🧠 Sending relevant information to Groq...")
response = llm.invoke(dynamic_prompt)

print("\n✨ Output from the Agent:")
print(response.content)