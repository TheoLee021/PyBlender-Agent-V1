import os
import chromadb
from chromadb.utils import embedding_functions

class RAGClient:
    def __init__(self, persist_path="chroma_db", collection_name="blender_api"):
        self.client = chromadb.PersistentClient(path=persist_path)
        
        # Use OpenAI's embedding function
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-3-small"
        )
        
        # Get or create collection (though generally we assume it exists)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )

    def query(self, text, n_results=5):
        """
        Query the vector DB for relevant context.
        Returns a formatted string of the top results.
        """
        results = self.collection.query(
            query_texts=[text],
            n_results=n_results
        )
        
        # results structure is a dict of lists: 
        # {'ids': [['id1', ...]], 'metadatas': [[{'k':'v'}, ...]], 'documents': [['text', ...]], ...}
        
        ids = results.get('ids', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        documents = results.get('documents', [[]])[0]
        
        formatted_results = []
        
        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            content = documents[i] if i < len(documents) else ""
            
            # Filter metadata
            # We want: id, url, type. We discard: title, module, description.
            # However, 'id' is already available as doc_id.
            
            url = meta.get('url', 'N/A')
            item_type = meta.get('type', 'N/A')
            
            # Construct the formatted string
            entry = (
                f"[Source: {doc_id}] (Type: {item_type}, URL: {url})\n"
                f"Content: {content}\n"
                "---"
            )
            formatted_results.append(entry)
            
        return "\n".join(formatted_results)
