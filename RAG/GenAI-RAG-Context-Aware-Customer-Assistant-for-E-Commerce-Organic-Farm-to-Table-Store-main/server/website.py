from flask import render_template, send_from_directory, redirect
from time import time
from os import urandom, path

class Website:
    def __init__(self, app) -> None:
        self.app = app

        # Set the template folder
        template_dir = path.abspath(path.join(path.dirname(__file__), '..', 'client', 'html'))
        self.app.jinja_loader.searchpath.append(template_dir)
        
        self.routes = {
            '/': {
                'function': lambda: redirect('/chat'),
                'methods': ['GET', 'POST']
            },
            '/chat/': {
                'function': self._index,
                'methods': ['GET', 'POST']
            },
            '/chat/<conversation_id>': {
                'function': self._chat,
                'methods': ['GET', 'POST']
            },
            '/client/<path:filename>': {  # Add this route
                'function': self._serve_static,
                'methods': ['GET']
            }
        }


    def _chat(self, conversation_id):
        if '-' not in conversation_id:
            return redirect('/chat')
        return render_template('index.html', chat_id=conversation_id)

    def _index(self):
        chat_id = f'{urandom(4).hex()}-{urandom(2).hex()}-{urandom(2).hex()}-{urandom(2).hex()}-{hex(int(time() * 1000))[2:]}'
        return render_template('index.html', chat_id=chat_id)

    def _serve_static(self, filename):
        return send_from_directory(self.app.static_folder, filename)

    def _assets(self, folder: str, file: str):
        try:
            file_path = path.join(path.dirname(__file__), '..', 'client', folder, file)
            return send_file(file_path, as_attachment=False)
        except FileNotFoundError:
            return "File not found", 404