import chromadb
from chromadb.config import Settings
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.chains.conversational_retrieval.prompts import CONDENSE_QUESTION_PROMPT
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from typing import Dict, Any 
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class CustomConversationBufferMemory(ConversationBufferMemory):
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        # Only save the 'answer' part of the output
        super().save_context(inputs, {"response": outputs["answer"]})

class RAGChatbot:
    def __init__(self, openai_api_key, collection_name, persist_directory, system_prompt_file):
        self.openai_api_key = openai_api_key
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.load_system_prompt(system_prompt_file)
        self.setup_langchain()

    def load_system_prompt(self, system_prompt_file):
        try:
            with open(system_prompt_file, 'r') as file:
                self.system_prompt = file.read().strip()
            logging.info(f"System prompt loaded from {system_prompt_file}")
        except FileNotFoundError:
            logging.error(f"System prompt file not found: {system_prompt_file}")
            self.system_prompt = "You are a helpful assistant."

    def setup_langchain(self):
        try:
            # Initialize the embedding model
            self.embedding_function = OpenAIEmbeddings(openai_api_key=self.openai_api_key)
            logging.info("Embedding function initialized.")

            # Initialize Chroma client
            self.chroma_client = chromadb.Client(Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory
            ))
            logging.info("Chroma client initialized.")

            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function.embed_documents
            )
            logging.info("Collection initialized or retrieved.")

            # Initialize Chroma with the embedding function and existing collection
            self.vectorstore = Chroma(
                client=self.chroma_client,
                collection_name=self.collection_name,
                embedding_function=self.embedding_function,
            )
            logging.info("Vectorstore initialized.")

            # Initialize ChatOpenAI
            self.llm = ChatOpenAI(temperature=0.7, openai_api_key=self.openai_api_key)
            logging.info("ChatOpenAI initialized.")

            # Initialize custom ConversationBufferMemory
            self.memory = CustomConversationBufferMemory(
                memory_key="chat_history",
                input_key="question",
                return_messages=True
            )
            logging.info("CustomConversationBufferMemory initialized.")

            # Create a custom prompt
            custom_prompt = PromptTemplate(
                template="""
                System: {system_prompt}

                Chat History:
                {chat_history}

                Human: {question}

                Context: {context}

                Assistant: Based on the above information, here's my response:
                """,
                input_variables=["system_prompt", "chat_history", "question", "context"]
            )

            # Create the question generator and QA chains
            question_generator = LLMChain(llm=self.llm, prompt=CONDENSE_QUESTION_PROMPT)
            doc_chain = load_qa_chain(self.llm, chain_type="stuff", prompt=custom_prompt)

            # Create the final chain
            self.qa_chain = ConversationalRetrievalChain(
                retriever=self.vectorstore.as_retriever(),
                combine_docs_chain=doc_chain,
                question_generator=question_generator,
                return_source_documents=True,
                memory=self.memory
            )
            logging.info("Custom ConversationalRetrievalChain initialized successfully.")
        except Exception as e:
            logging.error(f"Error in setup_langchain: {e}", exc_info=True)
            raise

    def clear_collection(self):
        self.collection.delete(where={})
        logging.info("Collection cleared.")

    def add_or_update_documents(self, documents):
        texts = [doc["text"] for doc in documents]
        metadatas = [{"source": doc["source"]} for doc in documents]
        ids = [f"{doc['source']}_{hash(doc['text'])}" for doc in documents]
        
        # Generate embeddings
        embeddings = self.embedding_function.embed_documents(texts)
        
        # Add documents to the collection
        self.collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings
        )

    def query(self, user_message):
        # List of common greetings
        greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        
        # Log the incoming user message
        logging.debug(f"Received user message: {user_message}")
        
        # Check if the user message is a greeting
        if any(greet in user_message.lower().strip() for greet in greetings):
            logging.debug("Recognized as a greeting message.")
            return self.greet(), []

        logging.debug("Not a greeting message, proceeding with qa_chain.")
        
        try:
            # Prepare inputs for the qa_chain
            inputs = {
                "question": user_message,
                "chat_history": [],  # implement chat history if needed
                "system_prompt": self.system_prompt  # Include the system prompt

            }

            # Log the inputs to the qa_chain
            logging.debug(f"Inputs to qa_chain: {inputs}")

            # Ensure qa_chain is called and response is received
            response = self.qa_chain(inputs)
            logging.debug(f"Response from qa_chain: {response}")
            
            # Extract answer and source documents from response
            answer = response.get('answer', 'No answer found')
            source_documents = response.get('source_documents', [])
            
            # Log the response from the qa_chain
            logging.debug(f"Answer from qa_chain: {answer}")
            
            # Log the source documents
            for i, doc in enumerate(source_documents):
                source = doc.metadata.get('source', 'unknown')
                content = doc.page_content[:100]  # First 100 characters
                logging.info(f"Document {i+1}:")
                logging.info(f"  Source: {source}")
                logging.info(f"  Content preview: {content}...")
            
            # Update memory
            self.memory.chat_memory.add_user_message(user_message)
            self.memory.chat_memory.add_ai_message(answer)

            return answer, source_documents
        except Exception as e:
            logging.error(f"Error in qa_chain processing: {e}", exc_info=True)
            return "There was an error processing your request.", []
    

    def get_all_documents(self):
        results = self.collection.get()
        documents = []
        for i in range(len(results['ids'])):
            documents.append({
                "id": results['ids'][i],
                "content": results['documents'][i],
                "metadata": results['metadatas'][i] if results['metadatas'] else {}
            })
        return documents

    def add_documents(self, documents):
        texts = [doc["text"] for doc in documents]
        metadatas = [{"source": doc["source"]} for doc in documents]
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas)
        self.chroma_client.persist()

    def greet(self):
        return ("Hello! Welcome to Desi Bazar Agro Ltd - your trusted local farm-to-table organic food producer! I am a GPT-based AI with custom knowledge about this business. "
                "How can I assist you today?")
