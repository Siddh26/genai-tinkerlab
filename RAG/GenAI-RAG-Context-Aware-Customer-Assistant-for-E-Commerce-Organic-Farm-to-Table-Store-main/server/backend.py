from flask import request, jsonify
from datetime import datetime
from requests import get, post
import os
import logging
import json
from .rag_chatbot import RAGChatbot
import requests


# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Backend_Api:
    def __init__(self, app, config: dict) -> None:
        self.app = app
        self.config = config
        self.openai_key = os.getenv("OPENAI_API_KEY") or config['openai_key']
        self.openai_api_base = os.getenv("OPENAI_API_BASE") or config['openai_api_base']
        self.proxy = config['proxy']
        
        # Initialize RAGChatbot
        self.chatbot = RAGChatbot(
            openai_api_key=self.openai_key,
            collection_name=config["chroma_db"]["collection_name"],
            persist_directory=config["chroma_db"]["persist_directory"],
            system_prompt_file=os.path.join(os.path.dirname(__file__), '..', 'system_prompt.txt')
        )
        
        self.routes = {
            '/health': {'function': self.health_check, 'methods': ['GET']},
            '/webhook': {'function': self.webhook, 'methods': ['POST']},
            '/backend-api/v2/conversation': {'function': self.conversation, 'methods': ['POST']},
            '/create-thread': {'function': self.create_thread, 'methods': ['POST']},
            '/add-message-to-thread': {'function': self.add_message_to_thread, 'methods': ['POST']},
            '/run-assistant': {'function': self.run_assistant, 'methods': ['POST']}
        }

        if not self.openai_key:
            raise ValueError("No OpenAI API key found in environment variables or config file.")
        
        if not self.openai_api_base:
            raise ValueError("No OpenAI API base URL found in environment variables or config file.")
        
        self.register_routes()

    def register_routes(self):
        for route, options in self.routes.items():
            self.app.add_url_rule(route, view_func=options['function'], methods=options['methods'])

    def health_check(self):
        if self.chatbot is None:
            return jsonify({'status': 'Chatbot is not initialized'}), 500
        try:
            all_docs = self.chatbot.get_all_documents()
            return jsonify({'status': 'Chatbot is initialized', 'document_count': len(all_docs)}), 200
        except Exception as e:
            logging.error(f"Error fetching documents: {e}", exc_info=True)
            return jsonify({'status': 'Error fetching documents', 'error': str(e)}), 500

    def webhook(self):
        if self.chatbot is None:
            return jsonify({'message': 'Chatbot is not initialized. Please check the logs.'}), 500

        data = request.json
        user_message = data.get('message', '').strip()
        logging.debug(f"Received message for webhook: {user_message}")
        try:
            answer, source_documents = self.chatbot.query(user_message)
            logging.debug(f"Response from chatbot: {answer}")
            return jsonify({'message': answer})
        except Exception as e:
            logging.error(f"Error processing message: {e}", exc_info=True)
            return jsonify({'message': 'Error processing your request.'}), 500

    def conversation(self):
        try:
            data = request.json
            logging.debug(f"Received data for conversation: {data}")
            user_message = data.get('message', '').strip()
            selected_model = data.get('model', 'gpt-3.5-turbo')  # Get selected model from frontend
            logging.debug(f"Extracted user message: '{user_message}'")

            if not user_message:
                logging.debug("User message is empty, returning greeting response.")
                return jsonify({'response': self.chatbot.greet()})

            jailbreak = data.get('jailbreak', False)
            internet_access = data.get('meta', {}).get('content', {}).get('internet_access', False)
            _conversation = data.get('meta', {}).get('content', {}).get('conversation', [])
            prompt = data.get('meta', {}).get('content', {}).get('parts', [{}])[0]
            current_date = datetime.now().strftime("%Y-%m-%d")
            system_message = 'You are a helpful assistant.'

            extra = []
            if internet_access:
                search = get('https://ddg-api.herokuapp.com/search', params={
                    'query': prompt.get("content", ""),
                    'limit': 3,
                })

                blob = ''
                for index, result in enumerate(search.json()):
                    blob += f'[{index}] "{result["snippet"]}"\nURL:{result["link"]}\n\n'

                date = datetime.now().strftime('%d/%m/%y')
                blob += f'current date: {date}\n\nInstructions: Using the provided web search results, write a comprehensive report...\n'
                extra.append({'role': 'system', 'content': blob})
            
            # messages = [{'role': 'system', 'content': system_message}]

            # for part in _conversation:
            #     messages.append({
            #         'role': part.get('role', 'user'),
            #         'content': part.get('content', '')
            #     })

            # messages.extend(extra)

            # if not prompt.get('content'):
            #     greeting = self.chatbot.greet()
            #     logging.debug("Returning greeting response")
            #     return jsonify({'response': greeting})

            # # Use RAG pipeline for local knowledge
            # logging.debug(f"Prompt content: {prompt.get('content', '')}")
            # rag_answer, source_documents = self.chatbot.query(prompt.get('content', ''))
            # logging.debug(f"RAG Answer: {rag_answer}")
           
            # Use RAG pipeline for local knowledge
            logging.debug(f"Using RAG pipeline for: {user_message}")
            rag_answer, source_documents = self.chatbot.query(user_message)
            logging.debug(f"RAG Answer: {rag_answer}")

            # If RAG answer is successful, return it without calling OpenAI API
            if rag_answer != "There was an error processing your request.":
                return jsonify({'response': rag_answer}), 200

            # Prepare messages for GPT
            messages = [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': user_message},
                {'role': 'assistant', 'content': f"Local knowledge base information: {rag_answer}"}
            ]

            # Make the API call to OpenAI
            try:
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {self.openai_key}'},
                    json={
                        'model': selected_model,
                        'messages': messages
                    },
                    timeout=30
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logging.error(f"Error calling OpenAI API: {e}")
                return jsonify({'response': rag_answer}), 200  # Fall back to RAG answer if API call fails

            if response.status_code == 200:
                gpt_resp = response.json()
                choices = gpt_resp.get('choices', [])
                if choices:
                    message_content = choices[0].get('message', {}).get('content', '')
                    logging.debug(f"GPT response: {message_content}")
                    return jsonify({'response': message_content}), 200
                else:
                    raise ValueError("No choices found in GPT response")
            else:
                return jsonify({
                    'error': response.json(),
                    'status_code': response.status_code
                }), response.status_code

        except Exception as e:
            logging.error(f"Error in conversation: {e}", exc_info=True)
            return jsonify({'message': 'Error processing your request.', 'error': str(e)}), 500
        
    def create_thread(self):
        response = post(
            'https://api.openai.com/v1/threads',
            headers={
                'Authorization': f'Bearer {self.openai_key}',
                'OpenAI-Beta': 'assistants=v2',
                'Content-Type': 'application/json'
            }
        )
        return jsonify(response.json())

    def add_message_to_thread(self):
        data = request.json
        thread_id = data.get('thread_id')
        message = data.get('message')
        
        if not thread_id or not message:
            return jsonify({'error': 'Missing thread_id or message'}), 400

        response = post(
            f'https://api.openai.com/v1/threads/{thread_id}/messages',
            json={
                'role': 'user',
                'content': [{'type': 'text', 'text': message}]
            },
            headers={
                'Authorization': f'Bearer {self.openai_key}',
                'OpenAI-Beta': 'assistants=v2',
                'Content-Type': 'application/json'
            }
        )
        return jsonify(response.json())

    def run_assistant(self):
        data = request.json
        thread_id = data.get('thread_id')
        
        if not thread_id:
            return jsonify({'error': 'Missing thread_id'}), 400

        run_response = post(
            f'https://api.openai.com/v1/threads/{thread_id}/runs',
            json={'assistant_id': 'asst_CfpSBa7E3rqGcOAVsSDTheiy'},
            headers={
                'Authorization': f'Bearer {self.openai_key}',
                'OpenAI-Beta': 'assistants=v2',
                'Content-Type': 'application/json'
            }
        )

        run_data = run_response.json()
        run_id = run_data.get('id')
        
        if not run_id:
            return jsonify({'error': 'Failed to start assistant run', 'response': run_data}), 500

        return jsonify({'run_id': run_id, 'status': run_data.get('status')})

def init_backend(app):
    config_path = os.getenv("CONFIG_PATH", "config.json")
    with open(config_path) as config_file:
        config = json.load(config_file)

    backend_api = Backend_Api(app, config)
    return backend_api
