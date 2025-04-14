# from flask import Flask, request, jsonify, send_from_directory
# import os
# import json
# from server.rag_chatbot import RAGChatbot
# from dotenv import load_dotenv
# import logging

# # Configure logging
# logging.basicConfig(level=logging.DEBUG)

# # Load environment variables from .env file
# load_dotenv()

# app = Flask(__name__, static_folder='client', static_url_path='/client')

# # Load configuration
# with open('config.json', 'r') as config_file:
#     config = json.load(config_file)

# # Load API key from environment variable
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# if not OPENAI_API_KEY:
#     raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

# # Initialize the RAG chatbot
# try:
#     chatbot = RAGChatbot(
#         OPENAI_API_KEY,
#         collection_name=config['chroma_db']['collection_name'],
#         persist_directory=config['chroma_db']['persist_directory'],
#         system_prompt_file="system_prompt.txt"  
#     )
#     logging.info("RAG chatbot initialized successfully")
# except Exception as e:
#     logging.error(f"Error initializing RAG chatbot: {e}")
#     chatbot = None

# @app.route('/')
# def index():
#     return send_from_directory('client/html', 'index.html')

# @app.route('/health', methods=['GET'])
# def health_check():
#     if chatbot is None:
#         return jsonify({'status': 'Chatbot is not initialized'}), 500
#     try:
#         all_docs = chatbot.get_all_documents()
#         return jsonify({'status': 'Chatbot is initialized', 'document_count': len(all_docs)}), 200
#     except Exception as e:
#         logging.error(f"Error fetching documents: {e}", exc_info=True)
#         return jsonify({'status': 'Error fetching documents', 'error': str(e)}), 500

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     if chatbot is None:
#         return jsonify({'message': 'Chatbot is not initialized. Please check the logs.'}), 500

#     data = request.json
#     user_message = data['text']
#     try:
#         answer, source_documents = chatbot.query(user_message)
#         return jsonify({'message': answer})
#     except Exception as e:
#         logging.error(f"Error processing message: {e}", exc_info=True)
#         return jsonify({'message': 'Error processing your request.'}), 500

# @app.route('/backend-api/v2/conversation', methods=['POST'])
# def conversation():
#     if chatbot is None:
#         return jsonify({'message': 'Chatbot is not initialized. Please check the logs.'}), 500

#     data = request.json
#     user_message = data.get('message', '')
    
#     # Check if this is a new conversation
#     if not user_message:
#         greeting = chatbot.greet()
#         return jsonify({'response': greeting})

#     try:
#         answer, source_documents = chatbot.query(user_message)
#         return jsonify({'response': answer})
#     except Exception as e:
#         logging.error(f"Error processing message: {e}", exc_info=True)
#         return jsonify({'message': 'Error processing your request.'}), 500

# if __name__ == '__main__':
#     app.run(
#         debug=config['site_config']['debug'],
#         host=config['site_config']['host'],
#         port=config['site_config']['port']
#     )
