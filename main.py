from fastapi import FastAPI, File, UploadFile, Form
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
from typing import Optional, List, Dict, Any
import re

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

# API configuration
# Use AI_BUILDER_TOKEN in deployment, SUPER_MIND_API_KEY for local development
API_KEY = os.getenv("AI_BUILDER_TOKEN") or os.getenv("SUPER_MIND_API_KEY")
SEARCH_API_URL = "https://space.ai-builders.com/backend/v1/search/"
TRANSCRIPTION_API_URL = "https://space.ai-builders.com/backend/v1/audio/transcriptions"

# Initialize OpenAI client with custom base URL
client = OpenAI(
    api_key=API_KEY,
    base_url="https://space.ai-builders.com/backend"
)

# ===== HELPER FUNCTIONS =====

def web_search(keywords: List[str], max_results: int = 5) -> dict:
    """Performs a web search using the internal search API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "keywords": keywords,
        "max_results": max_results
    }
    
    try:
        response = requests.post(SEARCH_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def search_schools_by_zip(zip_code: str) -> List[Dict]:
    """Search for top 10 schools in a ZIP code area."""
    print(f"[Search] Searching for top 10 schools in ZIP {zip_code}")
    
    # Search for schools in this ZIP code
    search_results = web_search([f"top rated schools in {zip_code} area", f"best private schools {zip_code}"], max_results=8)
    
    # Use AI to extract school names and basic info
    prompt = f"""Based on the following search results, extract the top 10 schools (if available) in ZIP code {zip_code}.
    
Search results:
{json.dumps(search_results, indent=2)}

Return a JSON array of schools with this format:
[
  {{
    "name": "School Name",
    "type": "Private/Public",
    "grade_range": "K-12",
    "brief_description": "One sentence description"
  }}
]

Only return valid JSON array, no additional text."""

    response = client.chat.completions.create(
        model="supermind-agent-v1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    content = response.choices[0].message.content
    
    # Extract JSON from response
    try:
        # Try to find JSON array in the response
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            schools = json.loads(json_match.group())
            return schools[:10]  # Return top 10
    except:
        pass
    
    return []

def get_school_details(school_name: str) -> Dict:
    """Get detailed information about a specific school."""
    print(f"[Search] Getting details for school: {school_name}")
    
    # Search for comprehensive school information
    search_keywords = [
        f"{school_name} tuition fees admission",
        f"{school_name} ranking academic programs",
        f"{school_name} core values mission",
        f"{school_name} official website information"
    ]
    
    search_results = web_search(search_keywords, max_results=8)
    
    # Use AI to compile detailed information
    prompt = f"""Based on the following search results about {school_name}, compile comprehensive information.

Search results:
{json.dumps(search_results, indent=2)}

Return a JSON object with this structure:
{{
  "name": "{school_name}",
  "website": "official website URL",
  "tuition": "费用信息 (annual costs)",
  "description": "学校介绍 (2-3 sentences)",
  "official_data": "官方数据 (enrollment, founded year, etc)",
  "rating": "学校评价 (overall rating and reviews)",
  "academic_ranking": "学术排名 (national/state rankings)",
  "school_info": "私校信息 (private school specific info)",
  "community": "社区信息 (community and location)",
  "college_placement": "升学情况 (college matriculation)",
  "core_values": "核心价值观 (mission and values)",
  "grade_range": "年级范围",
  "type": "Public/Private"
}}

Return valid JSON only."""

    response = client.chat.completions.create(
        model="supermind-agent-v1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    content = response.choices[0].message.content
    
    try:
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            details = json.loads(json_match.group())
            return details
    except Exception as e:
        print(f"Error parsing school details: {e}")
    
    return {"name": school_name, "error": "Could not retrieve details"}

# ===== REQUEST/RESPONSE MODELS =====

class SchoolSearchRequest(BaseModel):
    query: str
    search_type: str  # "zip" or "name"

class SchoolDetailsRequest(BaseModel):
    school_name: str

class ChatWithSchoolsRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ApplicationQuestionRequest(BaseModel):
    school_name: str
    school_context: str
    question: str
    student_profile: Dict[str, Any]

class InterviewQuestionsRequest(BaseModel):
    school_name: str
    school_context: str
    student_profile: Dict[str, Any]

class TranscriptionRequest(BaseModel):
    question: str
    school_context: str
    student_profile: Dict[str, Any]
    transcription: str

# ===== ROUTES =====

@app.get("/")
async def root():
    """Serve the main application."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/api/schools/search")
async def search_schools(request: SchoolSearchRequest):
    """Search for schools by ZIP code or name."""
    try:
        if request.search_type == "zip":
            schools = search_schools_by_zip(request.query)
            return {
                "success": True,
                "search_type": "zip",
                "query": request.query,
                "schools": schools
            }
        else:  # search by name
            details = get_school_details(request.query)
            return {
                "success": True,
                "search_type": "name",
                "query": request.query,
                "school": details
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/schools/details")
async def get_details(request: SchoolDetailsRequest):
    """Get detailed information about a specific school."""
    try:
        details = get_school_details(request.school_name)
        return {
            "success": True,
            "school": details
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/schools/chat")
async def chat_about_schools(request: ChatWithSchoolsRequest):
    """Chat with AI about schools."""
    try:
        # Build context-aware prompt
        system_prompt = """You are a helpful assistant for school research. 
Answer questions about schools, admissions, rankings, and education.
Be informative and helpful for parents researching schools."""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if request.context:
            messages.append({"role": "system", "content": f"Context: {request.context}"})
        
        messages.append({"role": "user", "content": request.message})
        
        response = client.chat.completions.create(
            model="supermind-agent-v1",
            messages=messages,
            temperature=0.7
        )
        
        return {
            "success": True,
            "response": response.choices[0].message.content
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/application/analyze")
async def analyze_application_question(request: ApplicationQuestionRequest):
    """Analyze and answer an application question."""
    try:
        prompt = f"""You are an expert college admissions consultant helping a student write their school application.

School: {request.school_name}
School Context: {request.school_context}

Student Profile:
{json.dumps(request.student_profile, indent=2)}

Application Question:
{request.question}

Please provide:
1. Analysis of what the question is asking for
2. Key points to address based on the school's values and the student's profile
3. A well-written response (300-500 words) that:
   - Highlights relevant experiences and qualities from the student's profile
   - Aligns with the school's core values and mission
   - Shows genuine interest and fit
   - Is authentic and personal
   - Demonstrates thoughtfulness and maturity

Format your response as JSON:
{{
  "analysis": "What the question is really asking",
  "key_points": ["point 1", "point 2", "point 3"],
  "suggested_response": "The full essay response here",
  "tips": ["tip 1", "tip 2"]
}}"""

        response = client.chat.completions.create(
            model="supermind-agent-v1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # Try to parse JSON
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "success": True,
                    "analysis": result
                }
        except:
            pass
        
        # If JSON parsing fails, return as plain text
        return {
            "success": True,
            "analysis": {
                "suggested_response": content
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/interview/generate")
async def generate_interview_questions(request: InterviewQuestionsRequest):
    """Generate sample interview questions for a school."""
    try:
        prompt = f"""Generate 8 realistic interview questions that {request.school_name} might ask during a student interview.

School Context: {request.school_context}

Student Profile:
{json.dumps(request.student_profile, indent=2)}

Consider the school's values, the student's background, and typical private school interview questions.
Include a mix of:
- Questions about academic interests
- Questions about personal qualities and character
- Questions about why they're interested in this school
- Questions about extracurricular activities
- Questions about challenges and growth

Return as JSON array:
[
  {{"question": "Question 1", "category": "Academic"}},
  {{"question": "Question 2", "category": "Personal"}},
  ...
]"""

        response = client.chat.completions.create(
            model="supermind-agent-v1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        
        try:
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                questions = json.loads(json_match.group())
                return {
                    "success": True,
                    "questions": questions
                }
        except:
            pass
        
        return {
            "success": False,
            "error": "Could not generate questions"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/interview/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """Transcribe audio file."""
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{audio_file.filename}"
        with open(temp_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Call transcription API
        headers = {
            "Authorization": f"Bearer {API_KEY}"
        }
        
        with open(temp_path, "rb") as audio:
            files = {"audio_file": audio}
            data = {"model": "whisper-1"}
            
            response = requests.post(
                TRANSCRIPTION_API_URL,
                headers=headers,
                files=files,
                data=data
            )
            response.raise_for_status()
            result = response.json()
        
        # Clean up temp file
        os.remove(temp_path)
        
        return {
            "success": True,
            "transcription": result.get("text", "")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/interview/feedback")
async def get_interview_feedback(request: TranscriptionRequest):
    """Get AI feedback on interview response."""
    try:
        prompt = f"""You are an expert interview coach evaluating a student's interview response.

Question: {request.question}

School Context: {request.school_context}

Student Profile:
{json.dumps(request.student_profile, indent=2)}

Student's Response (transcribed):
{request.transcription}

Provide detailed feedback on:
1. Grammar and clarity
2. Relevance to the question
3. Alignment with school values
4. Strengths of the response
5. Areas for improvement
6. Specific suggestions

Format as JSON:
{{
  "overall_score": "8/10",
  "grammar": {{
    "score": "9/10",
    "feedback": "Grammar feedback here"
  }},
  "relevance": {{
    "score": "7/10",
    "feedback": "Relevance feedback here"
  }},
  "alignment": {{
    "score": "8/10",
    "feedback": "School alignment feedback here"
  }},
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "suggestions": ["specific suggestion 1", "specific suggestion 2"]
}}"""

        response = client.chat.completions.create(
            model="supermind-agent-v1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        
        content = response.choices[0].message.content
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                feedback = json.loads(json_match.group())
                return {
                    "success": True,
                    "feedback": feedback
                }
        except:
            pass
        
        return {
            "success": True,
            "feedback": {
                "overall_score": "N/A",
                "suggestions": [content]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
