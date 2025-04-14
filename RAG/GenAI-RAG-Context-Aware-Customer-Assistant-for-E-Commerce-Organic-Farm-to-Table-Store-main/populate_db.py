import os
import json
import argparse
from server.rag_chatbot import RAGChatbot
from dotenv import load_dotenv
from docx import Document
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Load configuration
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Load API key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def split_text(text, max_chunk_size=1000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    for word in words:
        if current_size + len(word) > max_chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for the space
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def main(clear_collection=False, max_chunk_size=None):
    # Initialize the RAG chatbot
    chatbot = RAGChatbot(
        OPENAI_API_KEY,
        collection_name=config['chroma_db']['collection_name'],
        persist_directory=config['chroma_db']['persist_directory'],
        system_prompt_file=config.get('system_prompt_file', None)  # Add this line if you have a system prompt file
    )

    if clear_collection:
        chatbot.clear_collection()
        logging.info("Collection cleared.")

    # Use max_chunk_size from config if not provided as an argument
    if max_chunk_size is None:
        max_chunk_size = config['rag_config'].get('max_chunk_size', 1000)
    
    logging.info(f"Using max chunk size: {max_chunk_size}")

    # Add predefined documents about Desi Bazar Agro
    predefined_docs = [
        "Desi Bazar Agro is a farm-to-table organic food business.",
        "We specialize in locally produced organic vegetables and fruits.",
        "Our produce is sourced from small-scale farmers in the local community.",
        "We offer a wide range of seasonal organic products.",
        "Desi Bazar Agro was founded in 2020 with a mission to promote sustainable agriculture.",
        "We have weekly home delivery every weekend from 3 PM to 10 PM.",
        "Our online ordering system allows customers to get fresh produce delivered to their doorstep.",
        "We also offer organic cooking classes using our fresh ingredients.",
    ]

    documents = [{"text": doc, "source": "predefined"} for doc in predefined_docs]
    logging.info(f"Added {len(predefined_docs)} predefined documents")

    # Directory containing DOCX files
    docx_directory = "/Users/glocktopus/Desktop/RAGchat/knowledgebase"  
    logging.info(f"Scanning directory: {docx_directory}")

    # Check the directory for DOCX files and add their contents
    docx_files_processed = 0
    total_chunks = 0
    for filename in os.listdir(docx_directory):
        if filename.endswith(".docx"):
            docx_path = os.path.join(docx_directory, filename)
            logging.info(f"Processing DOCX file: {filename}")
            try:
                extracted_text = extract_text_from_docx(docx_path)
                logging.debug(f"Extracted {len(extracted_text)} characters from {filename}")
                chunks = split_text(extracted_text, max_chunk_size)
                logging.info(f"Split {filename} into {len(chunks)} chunks")
                total_chunks += len(chunks)
                for i, chunk in enumerate(chunks):
                    documents.append({"text": chunk, "source": f"{filename}_chunk_{i+1}"})
                    logging.debug(f"{filename} - Chunk {i+1} preview: {chunk[:50]}...")
                docx_files_processed += 1
            except Exception as e:
                logging.error(f"Error processing {filename}: {str(e)}")

    logging.info(f"Total DOCX files processed: {docx_files_processed}")
    logging.info(f"Total chunks created: {total_chunks}")
    logging.info(f"Total documents (including predefined): {len(documents)}")

    # Add or update the documents in the ChromaDB collection
    logging.info(f"Adding or updating {len(documents)} documents in ChromaDB...")
    for doc in documents:
        logging.debug(f"Adding/updating document: {doc['text'][:50]}... (Source: {doc['source']})")
        chatbot.add_or_update_documents([doc])
    logging.info("Documents processed successfully in ChromaDB.")

    # Validate the database
    all_docs = chatbot.get_all_documents()
    logging.info(f"Total documents in database after update: {len(all_docs)}")
    
    if len(all_docs) == len(documents):
        logging.info("All documents successfully added to the database.")
    else:
        logging.warning(f"Mismatch in document count. Expected: {len(documents)}, Actual: {len(all_docs)}")

    # Print all documents for verification
    for doc in all_docs:
        print(f"Document ID: {doc['id']}")
        print(f"Content preview: {doc['content'][:100]}...")
        print(f"Metadata: {doc['metadata']}")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate the RAG database.")
    parser.add_argument('--clear', action='store_true', help='Clear the existing collection before adding new documents')
    parser.add_argument('--chunk-size', type=int, help='Maximum size of text chunks')
    args = parser.parse_args()

    main(clear_collection=args.clear, max_chunk_size=args.chunk_size)