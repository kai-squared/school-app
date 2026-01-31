# AI Agent Chat Application

A beautiful, modern web-based chat application powered by FastAPI and an AI agent with web search and page reading capabilities.

## Features

### AI Agent Capabilities
- Web Search: Real-time web search using internal search API
- Page Reading: Extract and read content from any web page
- Multi-step Reasoning: Agentic loop that can chain multiple tool calls
- Smart Tool Selection: LLM automatically decides when to use tools

### Chat Interface
- Beautiful Modern UI: Gradient backgrounds and smooth animations
- Chat History Panel: Manage multiple conversations
- Thinking Animation: Visual feedback while the agent is processing
- Message Persistence: Chat history saved in browser localStorage
- Responsive Design: Works on desktop and mobile

## Running the Application

Start the server:
```bash
cd /Users/kai/Projects/architect
source venv/bin/activate
uvicorn main:app --reload
```

The application will be available at http://localhost:8000

## Usage

### Web Interface

1. Open your browser and navigate to http://localhost:8000
2. Try asking questions like:
   - "Who won the Super Bowl?"
   - "What's the weather in Paris?"
   - "Search for the latest Python release, then read the changelog"

### API Endpoints

POST /chat - Send a message to the AI agent
GET /docs - Interactive API documentation
GET /openapi.json - OpenAPI schema at http://localhost:8000/openapi.json

## Architecture

Frontend: HTML, CSS, JavaScript in /static folder
Backend: FastAPI with OpenAI integration and tool system
Base URL: http://localhost:8000/
