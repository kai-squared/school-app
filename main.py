from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import requests
import json
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize OpenAI client with custom base URL
client = OpenAI(
    api_key=API_KEY,
    base_url="https://space.ai-builders.com/backend/v1"
)

# API configuration
# Use AI_BUILDER_TOKEN in deployment, SUPER_MIND_API_KEY for local development
API_KEY = os.getenv("AI_BUILDER_TOKEN") or os.getenv("SUPER_MIND_API_KEY")
SEARCH_API_URL = "https://space.ai-builders.com/backend/v1/search/"


# Web search function
def web_search(query: str) -> dict:
    """
    Performs a web search using the internal search API.
    
    Args:
        query: The search query string
        
    Returns:
        dict: Search results from the API
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "keywords": [query],
        "max_results": 3
    }
    
    try:
        response = requests.post(SEARCH_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# Read page function
def read_page(url: str) -> dict:
    """
    Fetches a web page and extracts the main text content.
    
    Args:
        url: The URL of the page to read
        
    Returns:
        dict: Extracted text content from the page
    """
    try:
        # Fetch the page
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text - remove extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit text length to avoid token limits (first 5000 characters)
        if len(text) > 5000:
            text = text[:5000] + "... (content truncated)"
        
        return {
            "url": url,
            "content": text,
            "length": len(text)
        }
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "url": url}


# Define the tool schema for the LLM
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the web for current information about a topic. Use this when you need up-to-date information or facts that you don't know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": "Fetches and reads the content of a specific web page. Use this when you need to read detailed information from a known URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the web page to read"
                    }
                },
                "required": ["url"]
            }
        }
    }
]


class ChatRequest(BaseModel):
    user_message: str


class ChatResponse(BaseModel):
    content: str
    tool_calls: list = None  # Optional field to show tool calls


class HelloRequest(BaseModel):
    input: str


@app.get("/")
async def root():
    """
    Serve the main chat application.
    """
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/hello")
async def hello(request: HelloRequest):
    """
    Simple endpoint that returns a greeting message with the provided input.
    """
    return {"message": f"Hello, World {request.input}"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint with full agentic loop.
    The LLM can call tools, receive results, and provide a final answer.
    Maximum of 3 turns to prevent infinite loops.
    """
    max_turns = 3
    
    # Initialize conversation with user message
    messages = [
        {"role": "user", "content": request.user_message}
    ]
    
    print(f"\n{'='*80}")
    print(f"[User] {request.user_message}")
    print(f"{'='*80}\n")
    
    # Agentic loop
    for turn in range(max_turns):
        print(f"[Turn {turn + 1}/{max_turns}]")
        
        # Make API call with current conversation history
        completion = client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = completion.choices[0].message
        
        # Add assistant's response to conversation history
        messages.append({
            "role": "assistant",
            "content": response_message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in (response_message.tool_calls or [])
            ] if response_message.tool_calls else None
        })
        
        # Check if the model wants to call tools
        if response_message.tool_calls:
            print(f"[Agent] Decided to call {len(response_message.tool_calls)} tool(s):")
            
            # Execute each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"  → Tool: '{function_name}'")
                print(f"  → Arguments: {function_args}")
                
                # Execute the tool
                if function_name == "web_search":
                    query = function_args.get("query", "")
                    print(f"  → Executing search for: '{query}'")
                    
                    # Call the web_search function
                    tool_result = web_search(query)
                    
                    print(f"  → [System] Tool Output: {json.dumps(tool_result, indent=2)[:200]}...")
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                    
                elif function_name == "read_page":
                    url = function_args.get("url", "")
                    print(f"  → Reading page: '{url}'")
                    
                    # Call the read_page function
                    tool_result = read_page(url)
                    
                    if "error" in tool_result:
                        print(f"  → [System] Error reading page: {tool_result['error']}")
                    else:
                        print(f"  → [System] Successfully read {tool_result.get('length', 0)} characters")
                        print(f"  → [System] Content preview: {tool_result.get('content', '')[:150]}...")
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                    
                else:
                    # Unknown tool
                    print(f"  → [System] Error: Unknown tool '{function_name}'")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"error": f"Unknown tool: {function_name}"})
                    })
            
            print()  # Empty line for readability
            
            # Continue the loop to get the LLM's response with tool results
            continue
        else:
            # No more tool calls - we have a final answer
            final_answer = response_message.content or ""
            print(f"[Agent] Final Answer: {final_answer}\n")
            
            # Print the complete message history
            print(f"{'='*80}")
            print("[MESSAGE HISTORY - Complete Conversation]")
            print(f"{'='*80}\n")
            
            for idx, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                print(f"--- Message {idx + 1}: {role.upper()} ---")
                
                if role == "user":
                    print(f"Content: {msg.get('content', '')}\n")
                
                elif role == "assistant":
                    content = msg.get("content")
                    tool_calls = msg.get("tool_calls")
                    
                    if content:
                        print(f"Content: {content}")
                    
                    if tool_calls:
                        print(f"Tool Calls ({len(tool_calls)} total):")
                        for tc in tool_calls:
                            func_name = tc.get("function", {}).get("name", "unknown")
                            func_args = tc.get("function", {}).get("arguments", "")
                            print(f"  • {func_name}({func_args})")
                    print()
                
                elif role == "tool":
                    tool_call_id = msg.get("tool_call_id", "unknown")
                    content = msg.get("content", "")
                    
                    # Try to parse and pretty-print JSON content
                    try:
                        parsed = json.loads(content)
                        content_preview = json.dumps(parsed, indent=2)[:500]
                        if len(json.dumps(parsed)) > 500:
                            content_preview += "\n... (truncated)"
                    except:
                        content_preview = content[:500]
                        if len(content) > 500:
                            content_preview += "... (truncated)"
                    
                    print(f"Tool Call ID: {tool_call_id}")
                    print(f"Result:\n{content_preview}\n")
            
            print(f"{'='*80}\n")
            
            return ChatResponse(content=final_answer)
    
    # If we've exhausted max_turns, return the last message
    print(f"[System] Max turns ({max_turns}) reached. Returning last response.\n")
    print(f"{'='*80}\n")
    
    return ChatResponse(content=messages[-1].get("content", "I apologize, but I couldn't complete your request within the allowed iterations."))
