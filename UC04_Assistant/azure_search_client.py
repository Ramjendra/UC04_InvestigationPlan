import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

load_dotenv()

class AzureSearchClient:
    def __init__(self):
        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.key = os.getenv("AZURE_SEARCH_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX")
        self.credential = AzureKeyCredential(self.key) if self.key else None
        
    def search_knowledge_base(self, query_text, top=3):
        if not self.endpoint or not self.key or not self.index_name:
            # SIMULATED DATA
            return [
                {
                    "title": "Standard Investigation Protocol for Bribery",
                    "content": "Protocol for BRI cases involves immediate documentation of all financial transactions...",
                    "score": 0.95
                },
                {
                    "title": "Interview Guide: Complainant",
                    "content": "When interviewing complainants in financial misconduct cases, focus on timeline and evidence...",
                    "score": 0.88
                }
            ]

        try:
            client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.credential)
            results = client.search(search_text=query_text, top=top)
            return [{"title": r.get("title"), "content": r.get("content"), "score": r.get("@search.score")} for r in results]
        except Exception as e:
            print(f"Azure Search error: {e}")
            return []
