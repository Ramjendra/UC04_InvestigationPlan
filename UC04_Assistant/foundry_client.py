try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("WARNING: azure-ai-projects or azure-identity not installed. Using local mocks.")
    AIProjectClient = None
    DefaultAzureCredential = None

class FoundryClient:
    def __init__(self, force_mock=None):
        import os
        self.connection_string = os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING")
        self.deployment_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
        
        # Use provided override, or detect from env
        if force_mock is not None:
            self.is_mock = force_mock
        else:
            self.is_mock = not self.connection_string or "your-connection-string" in self.connection_string or AIProjectClient is None

        if self.is_mock:
            print("INFO: FoundryClient initialized in MOCK mode.")
            self.client = None
            return
            
        try:
            if AIProjectClient is None:
                raise ImportError("AIProjectClient not available")
            self.client = AIProjectClient.from_connection_string(
                credential=DefaultAzureCredential(),
                conn_str=self.connection_string
            )
        except Exception as e:
            print(f"ERROR: Failed to initialize AIProjectClient: {e}. Falling back to MOCK mode.")
            self.is_mock = True
            self.client = None

    def get_chat_completions_client(self):
        """
        Returns a chat completions client or a mock version.
        """
        if self.is_mock:
            return MockInferenceClient()
        return self.client.inference.get_chat_completions_client()

class MockInferenceClient:
    def complete(self, messages, **kwargs):
        """
        Simulates a response from the AI.
        """
        import random
        responses = [
            "Based on the simulated data, the investigation is progressing according to the CELA guidelines.",
            "I have analyzed the case files. Would you like me to generate a draft investigation plan?",
            "The triage report indicates a high-severity allegation. I recommend immediate witness interviews.",
            "I've retrieved 3 relevant precedents from the knowledge base that match this case's profile."
        ]
        return MockResponse(random.choice(responses))

class MockResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)

class MockMessage:
    def __init__(self, content):
        self.content = content
