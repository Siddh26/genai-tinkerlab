
import os
import json
from server.rag_chatbot import RAGChatbot
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Load API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

# Initialize the RAG chatbot
chatbot = RAGChatbot(
    OPENAI_API_KEY,
    collection_name=config['chroma_db']['collection_name'],
    persist_directory=config['chroma_db']['persist_directory']
)

# View all documents
chatbot.get_all_documents()