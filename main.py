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
# The AI Builders Space backend expects /v1/chat/completions
client = OpenAI(
    api_key=API_KEY,
    base_url="https://space.ai-builders.com/backend/v1"
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

def search_schools_by_zip(zip_code: str, miles: int = 10) -> List[Dict]:
    """Quick search for schools - tries web search first, falls back to AI knowledge."""
    print(f"[Search] Quick search for schools within {miles} miles of ZIP {zip_code}")
    
    search_query = f"private schools near {zip_code} within {miles} miles"
    
    # Try web search first
    search_results = None
    try:
        search_results = web_search([search_query], max_results=5)
        if search_results and search_results.get('queries'):
            print(f"[Web Search] Got {len(search_results.get('queries', []))} query results")
    except Exception as e:
        print(f"[Web Search] Failed: {e}")
    
    # Build prompt based on whether we have search results
    if search_results and search_results.get('queries'):
        prompt = f"""Based on these search results, extract private schools near ZIP code {zip_code}.

Search results:
{json.dumps(search_results, indent=2)}

Return a JSON array with 8-10 schools:
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "brief_description": "One sentence"}},
  {{"name": "Another School", "type": "Private", "grade_range": "6-12", "brief_description": "One sentence"}}
]

Return valid JSON only."""
    else:
        # Fallback to AI's training data
        prompt = f"""Using your training data, list 8-10 well-known private schools typically within {miles} miles of ZIP code {zip_code}.

Return a JSON array:
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "brief_description": "One sentence about the school"}},
  {{"name": "Another School", "type": "Private", "grade_range": "6-12", "brief_description": "One sentence"}}
]

Return valid JSON only."""

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Provide school information concisely."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        
        content = response.choices[0].message.content
        if not content:
            print("[Error] Empty response")
            return []
            
        print(f"[AI Response] {content[:200]}...")
        
        # Clean markdown
        content = content.strip()
        if content.startswith("```"):
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.startswith("```")])
        
        # Extract JSON
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            schools = json.loads(json_match.group())
            print(f"[Success] Found {len(schools)} schools")
            return schools[:10]
            
    except Exception as e:
        print(f"[Error] Search failed: {e}")
        import traceback
        traceback.print_exc()
    
    return []


def search_schools_by_location(location: str, location_type: str = "city") -> List[Dict]:
    """Search for schools by city or state."""
    print(f"[Search] Searching for schools in {location_type}: {location}")
    
    search_query = f"private schools in {location}" if location_type == "city" else f"top private schools in {location} state"
    
    # Try web search first
    search_results = None
    try:
        search_results = web_search([search_query], max_results=6)
        if search_results and search_results.get('queries'):
            print(f"[Web Search] Got {len(search_results.get('queries', []))} query results")
    except Exception as e:
        print(f"[Web Search] Failed: {e}")
    
    # Build prompt
    if search_results and search_results.get('queries'):
        prompt = f"""Based on these search results, extract a list of private schools in {location}.

Search results:
{json.dumps(search_results, indent=2)}

Return a JSON array with 8-12 schools:
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "brief_description": "One sentence"}},
  {{"name": "Another School", "type": "Private", "grade_range": "6-12", "brief_description": "One sentence"}}
]

Return valid JSON only."""
    else:
        # Fallback to AI knowledge
        prompt = f"""Using your training data, list 8-12 well-known private schools in {location}.

Return a JSON array:
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "brief_description": "One sentence about the school"}},
  {{"name": "Another School", "type": "Private", "grade_range": "6-12", "brief_description": "One sentence"}}
]

Return valid JSON only."""

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Provide school information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        
        content = response.choices[0].message.content
        if not content:
            return []
            
        # Clean and extract JSON
        content = content.strip()
        if content.startswith("```"):
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.startswith("```")])
        
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            schools = json.loads(json_match.group())
            print(f"[Success] Found {len(schools)} schools in {location}")
            return schools[:12]
            
    except Exception as e:
        print(f"[Error] Search failed: {e}")
    
    return []

def get_school_details(school_name: str) -> Dict:
    """Get detailed school information - tries web search first, falls back to AI knowledge."""
    print(f"[Deep Search] Getting comprehensive details for: {school_name}")
    
    # Try web search first
    search_keywords = [
        f"{school_name} tuition fees admission",
        f"{school_name} academic ranking",
        f"{school_name} mission values"
    ]
    
    search_results = None
    try:
        search_results = web_search(search_keywords, max_results=5)
        if search_results and search_results.get('queries'):
            print(f"[Web Search] Got results from {len(search_results.get('queries', []))} queries")
    except Exception as e:
        print(f"[Web Search] Failed: {e}")
    
    # Build prompt based on whether we have search results
    if search_results and search_results.get('queries'):
        prompt = f"""Based on these search results about {school_name}, compile comprehensive information.

Search results:
{json.dumps(search_results, indent=2)}

Return a detailed JSON object with all available information:
{{
  "name": "{school_name}",
  "website": "official website URL",
  "tuition": "Annual tuition and fees",
  "description": "2-3 sentence description",
  "rating": "School reputation",
  "academic_ranking": "Rankings",
  "school_info": "Key facts: enrollment, founded, campus",
  "community": "Location info",
  "college_placement": "College matriculation",
  "core_values": "Mission and values",
  "grade_range": "Grades served",
  "type": "Private or Public"
}}

Return valid JSON only."""
    else:
        # Fallback to AI's training data
        prompt = f"""Using your training data, provide comprehensive information about {school_name}.

Return a detailed JSON object:
{{
  "name": "{school_name}",
  "website": "official website if known",
  "tuition": "Typical annual tuition range",
  "description": "2-3 sentence description of the school",
  "rating": "School's reputation and standing",
  "academic_ranking": "Known rankings or recognition",
  "school_info": "Key facts: enrollment size, founded year, campus",
  "community": "Location and community context",
  "college_placement": "Typical college matriculation",
  "core_values": "Mission statement and values",
  "grade_range": "Grade levels served",
  "type": "Private or Public"
}}

Be specific where possible. Return valid JSON only."""

    try:
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant providing school information. Be accurate and specific."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        if not content:
            print("[Error] Empty response")
            return {"name": school_name, "error": "Could not retrieve details"}
            
        print(f"[AI Response] {content[:200]}...")
        
        # Clean markdown
        content = content.strip()
        if content.startswith("```"):
            lines = content.split('\n')
            content = '\n'.join([line for line in lines if not line.startswith("```")])
        
        # Extract JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            details = json.loads(json_match.group())
            print(f"[Success] Retrieved info for {school_name}")
            return details
            
    except Exception as e:
        print(f"[Error] Failed: {e}")
        import traceback
        traceback.print_exc()
    
    return {"name": school_name, "description": "Information not available", "type": "Private"}

# ===== REQUEST/RESPONSE MODELS =====

class SchoolSearchRequest(BaseModel):
    query: str
    search_type: str  # "zip", "city", "state", or "name"
    miles: Optional[int] = 10  # default 10 miles for ZIP/city search

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
    """Search for schools by ZIP code, city, state, or name."""
    try:
        if request.search_type == "zip":
            # Validate ZIP code format
            if not re.match(r'^\d{5}$', request.query):
                return {
                    "success": False,
                    "error": "Invalid ZIP code. Please enter a 5-digit US ZIP code."
                }
            
            miles = request.miles if request.miles else 10
            schools = search_schools_by_zip(request.query, miles)
            return {
                "success": True,
                "search_type": "zip",
                "query": request.query,
                "miles": miles,
                "schools": schools
            }
        elif request.search_type in ["city", "state"]:
            schools = search_schools_by_location(request.query, request.search_type)
            return {
                "success": True,
                "search_type": request.search_type,
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
            model="gemini-2.5-pro",
            messages=messages,
            temperature=0.7
        )
        
        return {
            "success": True,
            "response": response.choices[0].message.content
        }
    except Exception as e:
        print(f"[Error] Chat: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/application/analyze")
async def analyze_application_question(request: ApplicationQuestionRequest):
    """Analyze and answer an application question."""
    try:
        prompt = f"""You are an expert admissions consultant helping a student write their private school application.

School: {request.school_name}
School Context: {request.school_context}

Student Profile:
{json.dumps(request.student_profile, indent=2)}

Application Question:
{request.question}

Write a response following these guidelines:
1. Use written English (formal, essay-style)
2. Write in simple, clear paragraphs that directly answer the question
3. Support points with specific examples from the student's profile
4. Show genuine interest and fit with the school's values
5. Keep it authentic and thoughtful
6. Length: 300-500 words
7. Structure: Introduction → Body paragraphs with examples → Conclusion

Also provide:
- Brief analysis of what the question is asking
- 3-4 key points to address

Format your response as JSON:
{{
  "analysis": "Brief explanation of what the question seeks to understand",
  "key_points": ["point 1", "point 2", "point 3", "point 4"],
  "suggested_response": "The full written response in essay format with clear paragraphs. Use \\n\\n for paragraph breaks.",
  "tips": ["writing tip 1", "writing tip 2"]
}}"""

        response = client.chat.completions.create(
            model="gemini-2.5-pro",
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

Consider the school's values and typical private school interview questions.
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
            model="gemini-2.5-pro",
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
        print(f"[Error] Question generation: {e}")
        import traceback
        traceback.print_exc()
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

Question Asked: {request.question}

School Context: {request.school_context}

Student Profile:
{json.dumps(request.student_profile, indent=2)}

Student's Transcribed Response:
{request.transcription}

Provide detailed feedback on:
1. Grammar and clarity - Is the response well-articulated?
2. Relevance to the question - Does it actually answer what was asked?
3. Alignment with school values - Does it show understanding of the school?
4. What the student did well
5. Specific areas to improve
6. Actionable suggestions for a better response

Format as JSON:
{{
  "overall_score": "X/10",
  "grammar": {{
    "score": "X/10",
    "feedback": "Grammar and clarity feedback"
  }},
  "relevance": {{
    "score": "X/10",
    "feedback": "How well it answers the question"
  }},
  "alignment": {{
    "score": "X/10",
    "feedback": "Connection to school values"
  }},
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["area to improve 1", "area to improve 2"],
  "suggestions": ["specific suggestion 1", "specific suggestion 2"]
}}"""

        # Use gemini without web search tools
        response = client.chat.completions.create(
            model="gemini-2.5-pro",
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
        print(f"[Error] Feedback generation: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
