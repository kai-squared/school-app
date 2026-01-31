# School Application Helper

An AI-powered assistant for US PK-12 school applications, helping students search for schools, write compelling applications, and prepare for interviews.

## Features

### 1. 🔍 School Search
- Search schools by ZIP code or exact name
- Get detailed school information and rankings
- Chat with AI to learn more about specific schools
- Save school information for application writing

### 2. ✍️ Application Writer
- Save and manage student profile
- Generate personalized responses to application questions
- Leverage school-specific information and values
- Get AI assistance tailored to your background

### 3. 🎤 Interview Preparation
- Generate tailored interview questions based on student profile and school
- Record up to 60-second audio responses
- Automatic transcription of your answers
- AI feedback on grammar, relevance, and alignment with school values

## Running the Application

Start the server:
```bash
cd /Users/kai/Projects/architect
source venv/bin/activate
uvicorn main:app --reload
```

The application will be available at http://localhost:8000

## Technology Stack

- **Backend**: FastAPI with OpenAI-compatible AI agent
- **Frontend**: Modern HTML, CSS, JavaScript
- **AI Model**: supermind-agent-v1 (with built-in web search)
- **API**: AI Builders Space Backend (https://space.ai-builders.com/backend)

## Current Status

**Skeleton Implementation Complete** ✅

The UI and navigation are fully functional with placeholder implementations for:
- School search with chat interface
- Application question writer with profile management
- Interview prep with audio recording and transcription
- Navigation between all three sections

**Next Steps**: Implement actual API integrations for each feature.

## API Endpoints

The app uses the following AI Builders Space APIs:
- `/v1/chat/completions` - Chat and question generation
- `/v1/search/` - School search functionality  
- `/v1/audio/transcriptions` - Audio transcription

## License

This project is for educational purposes.
