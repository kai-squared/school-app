from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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
import urllib.parse

# Load environment variables from .env file
load_dotenv()

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize FastAPI app
app = FastAPI()

# Global exception handler to prevent HTML error pages
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[GLOBAL ERROR] {request.url}: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=200,  # Return 200 to avoid default error pages
        content={
            "success": False,
            "error": "Service temporarily unavailable. Please try again in a moment.",
            "schools": []
        },
        headers={"Content-Type": "application/json"}
    )

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

def search_schools_by_zip(zip_code: str, miles: int = 10, exclude_schools: List[str] = []) -> List[Dict]:
    """Quick search for schools - 3-tier fallback: web search → AI knowledge → generic fallback."""
    print(f"[Search] Searching schools within {miles} miles of ZIP {zip_code}, excluding {len(exclude_schools)} schools")
    
    # Tier 1: Try web search
    search_results = None
    try:
        search_query = f"best private schools near ZIP code {zip_code} Niche ranking address"
        search_results = web_search([search_query], max_results=10)
        has_results = search_results and search_results.get('queries')
    except Exception as e:
        print(f"[Web Search] Failed: {e}")
        has_results = False
    
    exclude_clause = ""
    if exclude_schools:
        schools_list = ', '.join(exclude_schools[:10])
        exclude_clause = f"\n\nEXCLUDE these schools (already shown): {schools_list}"
    
    # Try with web search results
    if has_results:
        prompt = f"""Extract 10-15 private schools from these search results near ZIP {zip_code}.

Search Results:
{json.dumps(search_results, indent=2)[:4000]}
{exclude_clause}

Return ONLY a valid JSON array (no markdown, no extra text):
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "address": "Full Address", "website": "https://...", "niche_ranking": "A+ or #1 in State", "brief_description": "1-2 sentences"}},
  ...
]"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Return only valid JSON arrays, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            if content:
                schools = extract_json_array(content)
                if schools:
                    print(f"[Success - Web Search] Found {len(schools)} schools")
                    return schools[:15]
        except Exception as e:
            print(f"[Error - Web Search Path] {e}")
    
    # Tier 2: Fallback to AI knowledge base (no web search)
    print(f"[Tier 2 Fallback] Using AI knowledge base for ZIP {zip_code}")
    try:
        kb_prompt = f"""List 10 well-known private schools near ZIP code {zip_code} using your training data.
{exclude_clause}

Return ONLY a valid JSON array:
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "address": "City, State", "website": "https://...", "niche_ranking": "A+", "brief_description": "1-2 sentences"}},
  ...
]"""
        
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use only your training data. Return only valid JSON arrays."},
                {"role": "user", "content": kb_prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        if content:
            schools = extract_json_array(content)
            if schools:
                print(f"[Success - Knowledge Base] Found {len(schools)} schools")
                return schools[:15]
    except Exception as e:
        print(f"[Error - Knowledge Base Fallback] {e}")
    
    # Tier 3: Generic fallback message
    print(f"[Tier 3 Fallback] Using generic fallback for {zip_code}")
    return create_fallback_schools(zip_code)


def extract_json_array(content: str) -> List[Dict]:
    """Extract and parse JSON array from AI response."""
    try:
        content = content.strip()
        
        # Remove markdown code blocks
        if content.startswith("```"):
            content = re.sub(r'```[\w]*\n', '', content)
            content = re.sub(r'```$', '', content)
            content = content.strip()
        
        # Find JSON array
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            schools = json.loads(json_match.group())
            if isinstance(schools, list) and len(schools) > 0:
                return schools
    except json.JSONDecodeError as je:
        print(f"[JSON Parse Error] {je}")
    except Exception as e:
        print(f"[Extract Error] {e}")
    
    return None


def create_fallback_schools(location: str) -> List[Dict]:
    """Create a minimal fallback response when search fails."""
    return [
        {
            "name": f"Search results unavailable for {location}",
            "type": "Private",
            "grade_range": "K-12",
            "address": "Please try again or refine your search",
            "website": None,
            "niche_ranking": None,
            "brief_description": "We're experiencing high demand. Please try searching again in a moment, or try a different location."
        }
    ]


def search_schools_by_location(location: str, location_type: str = "city", exclude_schools: List[str] = []) -> List[Dict]:
    """Search for schools by city or state - 3-tier fallback: web search → AI knowledge → generic fallback."""
    print(f"[Search] Searching for schools in {location_type}: {location}, excluding {len(exclude_schools)} schools")
    
    # Tier 1: Try web search
    search_results = None
    try:
        if location_type == "city":
            search_query = f"best private schools in {location} Niche ranking address"
        else:
            search_query = f"top private schools in {location} state Niche ranking"
        
        search_results = web_search([search_query], max_results=12)
        has_results = search_results and search_results.get('queries')
    except Exception as e:
        print(f"[Web Search] Failed: {e}")
        has_results = False
    
    exclude_clause = ""
    if exclude_schools:
        schools_list = ', '.join(exclude_schools[:10])
        exclude_clause = f"\n\nEXCLUDE these schools (already shown): {schools_list}"
    
    # Try with web search results
    if has_results:
        prompt = f"""Extract 10-15 private schools from these search results in {location}.

Search Results:
{json.dumps(search_results, indent=2)[:4000]}
{exclude_clause}

Return ONLY a valid JSON array (no markdown, no extra text):
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "address": "Full Address", "website": "https://...", "niche_ranking": "A+ or #1 in State", "brief_description": "1-2 sentences"}},
  ...
]"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Return only valid JSON arrays, no markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            if content:
                schools = extract_json_array(content)
                if schools:
                    print(f"[Success - Web Search] Found {len(schools)} schools")
                    return schools[:15]
        except Exception as e:
            print(f"[Error - Web Search Path] {e}")
    
    # Tier 2: Fallback to AI knowledge base (no web search)
    print(f"[Tier 2 Fallback] Using AI knowledge base for {location}")
    try:
        kb_prompt = f"""List 10-15 well-known private schools in {location} using your training data.
{exclude_clause}

Return ONLY a valid JSON array:
[
  {{"name": "School Name", "type": "Private", "grade_range": "K-12", "address": "City, State", "website": "https://...", "niche_ranking": "A+", "brief_description": "1-2 sentences"}},
  ...
]"""
        
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use only your training data. Return only valid JSON arrays."},
                {"role": "user", "content": kb_prompt}
            ],
            temperature=0.3,
            timeout=20
        )
        
        content = response.choices[0].message.content
        if content:
            schools = extract_json_array(content)
            if schools:
                print(f"[Success - Knowledge Base] Found {len(schools)} schools")
                return schools[:15]
    except Exception as e:
        print(f"[Error - Knowledge Base Fallback] {e}")
    
    # Tier 3: Generic fallback message
    print(f"[Tier 3 Fallback] Using generic fallback for {location}")
    return create_fallback_schools(location)

def get_school_details(school_name: str) -> Dict:
    """Get detailed school information with comprehensive web search."""
    print(f"[Deep Search] Getting comprehensive details for: {school_name}")
    
    # Do comprehensive web search for this specific school
    search_query = f"{school_name} private school tuition admission ranking official website Niche rating"
    
    try:
        search_results = web_search([search_query], max_results=8)
        has_results = search_results and search_results.get('queries')
    except Exception as e:
        print(f"[Web Search] Failed: {e}")
        has_results = False
    
    # Single AI call to extract comprehensive details
    if has_results:
        prompt = f"""Extract comprehensive details about {school_name} from these search results.

Search Results:
{json.dumps(search_results, indent=2)}

Return ONLY a valid JSON object (no markdown):
{{
  "name": "{school_name}",
  "type": "Private",
  "grade_range": "K-12",
  "website": "official website URL",
  "address": "full address",
  "tuition": "Annual tuition with range if available (e.g., $35,000-$45,000)",
  "rating": "Niche rating or overall rating",
  "academic_ranking": "Academic ranking details",
  "school_info": "Enrollment, founding year, campus details",
  "community": "Community and diversity information",
  "college_placement": "College matriculation statistics",
  "core_values": "School's mission and core values",
  "niche_ranking": "Niche grade or ranking",
  "description": "Comprehensive 2-3 sentence description"
}}"""
    else:
        # Fallback to AI knowledge
        prompt = f"""Provide comprehensive details about {school_name} using your training data.

Return ONLY a valid JSON object:
{{
  "name": "{school_name}",
  "type": "Private",
  "grade_range": "K-12",
  "website": "school website",
  "address": "city, state",
  "tuition": "Estimated annual tuition",
  "rating": "Rating if known",
  "academic_ranking": "Ranking details",
  "school_info": "Key information",
  "community": "Community description",
  "college_placement": "College placement info",
  "core_values": "Core values",
  "niche_ranking": "Niche ranking if known",
  "description": "2-3 sentence description"
}}"""

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
    exclude_schools: Optional[List[str]] = []  # list of school names to exclude

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
        exclude_schools = request.exclude_schools or []
        
        if request.search_type == "zip":
            # Validate ZIP code format
            if not re.match(r'^\d{5}$', request.query):
                return {
                    "success": False,
                    "error": "Invalid ZIP code. Please enter a 5-digit US ZIP code.",
                    "schools": []
                }
            
            miles = request.miles if request.miles else 20
            schools = search_schools_by_zip(request.query, miles, exclude_schools)
            
            # Ensure we always have valid data
            if not schools or not isinstance(schools, list):
                schools = create_fallback_schools(request.query)
            
            return {
                "success": True,
                "search_type": "zip",
                "query": request.query,
                "miles": miles,
                "schools": schools
            }
        elif request.search_type in ["city", "state"]:
            schools = search_schools_by_location(request.query, request.search_type, exclude_schools)
            
            # Ensure we always have valid data
            if not schools or not isinstance(schools, list):
                schools = create_fallback_schools(request.query)
            
            return {
                "success": True,
                "search_type": request.search_type,
                "query": request.query,
                "schools": schools
            }
        else:  # search by name
            details = get_school_details(request.query)
            
            # Ensure we always have valid data
            if not details or not isinstance(details, dict):
                details = {
                    "name": request.query,
                    "description": "Details temporarily unavailable. Please try again.",
                    "type": "Private"
                }
            
            return {
                "success": True,
                "search_type": "name",
                "query": request.query,
                "school": details
            }
    except Exception as e:
        print(f"[ERROR] Search endpoint failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Always return valid JSON, never let it crash
        return {
            "success": False,
            "error": f"Search temporarily unavailable. Please try again in a moment.",
            "schools": create_fallback_schools(request.query if hasattr(request, 'query') else "search")
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
