Absolutely. Copy **everything inside the block below** into your `README.md`. **Do not copy anything before or after the block.** The README ends at `License`.

```
# PrepMate

**PrepMate is a privacy-first AI interview coach built for a friend preparing for SDE interviews.**

It takes a candidate's resume and a target job description, uses local RAG and an open-weight Gemma model to identify strengths and skill gaps, and then runs a short adaptive mock interview based on the candidate's profile.

> **Status:** Working MVP — Resume/JD analysis + local RAG + adaptive 2-question mock interview + final feedback report.

Built for the **Hacktoberfest 2026 DEV Challenge: Build for a Friend**.

## Problem

A friend preparing for software-engineering interviews may have a resume, a target job description, and a long list of topics to study. Generic interview tools often provide questions without grounding them in the candidate's actual background or the requirements of the target role.

PrepMate addresses this by connecting the candidate's resume, target job description, retrieved context, and interview performance into one personalized preparation workflow.

## Solution

PrepMate:

1. Extracts text from a resume PDF.
2. Accepts a target job description.
3. Creates local embeddings and indexes the content using FAISS.
4. Uses an open-weight Gemma model locally through Ollama.
5. Analyzes strengths, skill gaps, relevant experience, interview topics, and preparation priorities.
6. Starts a two-question adaptive mock interview.
7. Evaluates each answer for correctness, depth, clarity, and completeness.
8. Selects the next interview strategy based on the evaluation.
9. Generates a final feedback report with strengths, weaknesses, topics to revise, and next steps.

## Key Features

### Resume + Job Description Analysis

Upload a resume PDF and provide a target job description.

PrepMate produces:

- Strengths
- Skill gaps
- Relevant experience
- Interview topics
- Personalized preparation plan

### Local RAG

PrepMate uses:

- `sentence-transformers/all-MiniLM-L6-v2` for embeddings
- FAISS for vector similarity search
- In-memory storage for the current request/session

The resume and job description are processed locally and are not permanently stored by the application.

### Open-Weight Gemma

PrepMate uses:

- **Gemma 2B**
- **Ollama**
- Local inference
- No paid LLM API required

The model is used for analysis, interview question generation, answer evaluation, and feedback.

### Adaptive Mock Interview

The interview consists of two questions.

After each answer, PrepMate evaluates:

- Correctness
- Depth
- Clarity
- Completeness
- Overall score
- Strengths
- Missing concepts
- Feedback

The next question strategy is selected deterministically by the application based on the evaluation.

Possible strategies include:

- `reinforce_weakness`
- `follow_up`
- `harder_question`
- `same_topic`
- `new_topic`

This keeps the adaptive logic explainable while allowing Gemma to generate natural interview questions and evaluations.

### Final Feedback Report

After the second question, PrepMate generates a final report containing:

- Overall score
- Strengths
- Weaknesses
- Topics to revise
- Recommended next steps

## Architecture

```text
                    Browser
                       |
                       v
                Next.js Frontend
                       |
                       v
                FastAPI Backend
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
   PDF Extraction     RAG          Interview
        |              |              |
        |         Embeddings +        |
        |             FAISS           |
        |              |              |
        +--------------+--------------+
                       |
                       v
                 Ollama / Gemma
                       |
                       v
             Analysis + Evaluation
                       |
                       v
                Final Report
```

## Privacy

Privacy is an important part of PrepMate because resumes contain sensitive information.

Current behavior:

- Resume PDFs are processed in memory.
- Uploaded PDFs are not permanently stored by the application.
- Interview sessions are maintained in memory.
- No authentication system is currently required.
- No paid external LLM API is required.
- The application returns `stored: false` for analysis and interview responses.
- The included demo resume contains synthetic fictional data.

For local Ollama inference, the LLM processing stays on the developer's machine.

## Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic

### AI / RAG

- Gemma 2B
- Ollama
- Sentence Transformers
- FAISS
- NumPy

### Document Processing

- pypdf
- python-multipart

### Testing

- pytest

## Project Structure

```
PrepMate/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── store/
│   ├── data/
│   ├── tests/
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── package-lock.json
│
├── sample/
│   ├── DEMO_CANDIDATE.md
│   ├── README.md
│   ├── demo_resume.pdf
│   ├── job_description.txt
│   └── resume.txt
│
├── .env.example
├── .gitignore
└── README.md
```

## Local Setup

### Requirements

- Python 3.10+
- Node.js and npm
- Ollama
- Git

### 1. Clone the repository

```
git clone https://github.com/Sri-Indu/PrepMate.git
cd PrepMate
```

### 2. Backend setup

From the project root:

```
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example environment file:

```
copy ..\.env.example .env
```

The default local configuration uses:

```
LLM_PROVIDER=ollama
LLM_MODEL=gemma2:2b
LLM_BASE_URL=http://127.0.0.1:11434
```

### 4. Start Ollama and download Gemma

Install Ollama, then run:

```
ollama pull gemma2:2b
```

### 5. Start the FastAPI backend

From `backend/`:

```
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

Check:

```
http://127.0.0.1:8000/health
```

### 6. Frontend setup

Open another terminal:

```
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open:

```
http://localhost:3000
```

## Demo

The repository includes synthetic demo data in the `sample/` directory.

Use:

```
sample/demo_resume.pdf
sample/job_description.txt
```

Demo flow:

```
Resume PDF + Job Description
          ↓
    Resume Extraction
          ↓
       Local RAG
          ↓
      Gemma Analysis
          ↓
 Strengths + Skill Gaps
          ↓
   Start Mock Interview
          ↓
        Question 1
          ↓
      Answer Evaluation
          ↓
        Question 2
          ↓
      Answer Evaluation
          ↓
     Final Feedback
```

## Testing

Backend tests can be run with:

```
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

The current test suite contains **34 passing tests** covering:

- PDF extraction
- Chunking
- Embeddings/RAG behavior
- LLM integration
- Candidate analysis
- Interview session creation
- Answer evaluation
- Adaptive strategy selection
- Final interview report
- Error handling

The tests mock the LLM where appropriate so that the test suite does not require a live model for every test.

## Why Open-Source AI?

PrepMate uses an open-weight Gemma model through Ollama instead of depending on a paid hosted LLM API.

This matters because interview preparation can involve sensitive personal information such as resumes, employment history, skills, and career goals.

A local open-weight model provides:

- Greater control over data
- Local inference
- No mandatory paid API
- Reproducible development
- The ability to experiment with different open models

For this project, Gemma 2B provides a practical balance between capability and local hardware requirements.

## Hacktoberfest 2026

PrepMate was built for the **Hacktoberfest 2026 DEV Challenge: Build for a Friend**.

The project focuses on solving a real problem for a friend preparing for SDE interviews while demonstrating a meaningful use of open-source AI.

The core open-source AI component is the locally run Gemma model through Ollama, combined with local embeddings and FAISS-based retrieval.

## Current Limitations

This is an MVP and intentionally keeps the scope small.

Current limitations include:

- Mock interview is limited to two questions.
- No user authentication.
- No persistent interview history.
- Interview sessions are stored only in memory.
- No production deployment.
- No voice input.
- Local Ollama inference is required for the full AI workflow.
- Gemma 2B can occasionally produce incomplete or imperfect evaluations.

## Future Improvements

Possible future improvements include:

- Longer adaptive interview sessions
- Voice-based interviews
- Persistent user profiles and interview history
- Authentication
- More advanced agentic interview planning
- Better evaluation consistency
- Additional open-weight models
- Production deployment
- More detailed progress tracking
- Interview analytics and historical performance comparison

## License

This project is intended to be open source.

An appropriate open-source license can be added before broader distribution.