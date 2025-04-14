from flask import Flask
from .rag_chatbot import RAGChatbot
import os
from dotenv import load_dotenv

def create_app(config, register_routes=True):
    app = Flask(__name__, 
                static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'client')),
                static_url_path='/client')
    
    # Load environment variables
    load_dotenv()
    
    # Load API key from environment variable
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")
    
    # Initialize the RAG chatbot
    try:
        app.chatbot = RAGChatbot(
            openai_api_key=OPENAI_API_KEY,
            collection_name=config['chroma_db']['collection_name'],
            persist_directory=config['chroma_db']['persist_directory'],
            system_prompt_file=os.path.join(os.path.dirname(__file__), '..', 'system_prompt.txt')
        )
        app.logger.info("RAG chatbot initialized successfully")
    except Exception as e:
        app.logger.error(f"Error initializing RAG chatbot: {e}")
        app.chatbot = None
    
    # Only register routes if register_routes is True
    if register_routes:
        from .website import Website
        from .backend import Backend_Api

        # Initialize Website and register routes
        website = Website(app)
        for route, options in website.routes.items():
            app.add_url_rule(route, view_func=options['function'], methods=options['methods'])
        
        # Initialize Backend_Api and register routes
        backend_api = Backend_Api(app, config)
        for route, options in backend_api.routes.items():
            app.add_url_rule(route, view_func=options['function'], methods=options['methods'])
    
    return app
