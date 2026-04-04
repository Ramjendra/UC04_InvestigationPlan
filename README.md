# UC04 Investigation Assistant - Setup Guide

This project is an AI-powered Investigation Planning Assistant (UC-04) for the Microsoft UCM platform. It features integration with Azure AI Foundry and a premium Streamlit UI designed for Business and Regulatory Investigations.

## Project Structure

There are two versions of the application available in this repository:

1.  **Standard Edition (`app.py`)**: The primary enterprise-focused interface featuring Dynamics 365 styling, VerseAPI mocks, and integrated Copilot-style assistant.
2.  **Premium Assistant (`UC04_Assistant/app.py`)**: A focused assistant-first interface with a floating 🤖 button and a 35% width chat panel.

---

## Prerequisites
- **Python 3.9+**
- **Git**

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd UC04_InvestigationPlan
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## Configuration

### Environment Variables
1.  Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
2.  Open `.env` and fill in your credentials.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `AZURE_AI_PROJECT_CONNECTION_STRING` | Your Azure AI Foundry project connection string. | `your-connection-string` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | The deployment name of your GPT model (e.g., `gpt-4o`). | `gpt-4o` |
| `OLLAMA_BASE_URL` | Base URL if using a local Ollama instance (Fallback). | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | Model name for local Ollama. | `llama3.1` |

> [!NOTE]
> If `AZURE_AI_PROJECT_CONNECTION_STRING` is left as default or empty, the application will automatically run in **Simulated Mock** mode, which is perfect for demonstration without live cloud resources.

---

## Running the Application

### Option A: Standard Enterprise UI (Recommended)
```bash
streamlit run app.py
```

### Option B: Premium Assistant UI
```bash
# From the root directory
streamlit run UC04_Assistant/app.py
```

## Features
- **Live Azure Foundry**: Connects to real Azure AI Project services.
- **Simulated Mock Mode**: Uses local simulated data (perfect for disconnected demos).
- **Dynamics 365 Aesthetics**: Seamlessly integrates into enterprise environments.
- **Agentic Pipeline**: Multi-step investigation planning using enterprise-grade AI.
