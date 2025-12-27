# Mentors Mantra Test Generator

AI-powered test paper generator for JEE Main/Advanced preparation. Generates professionally formatted PDF test papers with MCQs and Numerical questions.

## Features

- 🤖 **LLM-Agnostic**: Switch between Gemini, OpenAI, or Claude by changing an environment variable
- 📄 **Professional PDFs**: LaTeX-rendered test papers with proper formatting
- ⚡ **Stable Generation**: AI returns JSON → Jinja2 renders LaTeX (no direct LaTeX from AI)
- 🎨 **Modern UI**: Glassmorphism dark theme with smooth animations

## Project Structure

```
Auto pdf/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── services/
│   │   ├── llm_engine.py    # LiteLLM integration
│   │   └── pdf_engine.py    # Jinja2 + pdflatex
│   ├── templates/
│   │   └── master.tex       # LaTeX template
│   ├── .env                 # API keys and model config
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── app/
    │   ├── page.tsx         # Main UI
    │   ├── layout.tsx
    │   └── globals.css      # Theme styles
    └── package.json
```

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys in .env
# Edit .env and add your API key(s)

# Install pdflatex (required for PDF generation)
# macOS: brew install --cask mactex-no-gui
# Ubuntu: sudo apt install texlive-latex-base texlive-fonts-recommended texlive-pictures

# Start the server
uvicorn main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Configuration

### Switching LLM Providers

Edit `backend/.env`:

```env
# Use Gemini
ACTIVE_MODEL="gemini/gemini-1.5-flash"
GEMINI_API_KEY="your-key"

# Or use OpenAI
ACTIVE_MODEL="openai/gpt-4o"
OPENAI_API_KEY="your-key"

# Or use Claude
ACTIVE_MODEL="anthropic/claude-3-sonnet-20240229"
ANTHROPIC_API_KEY="your-key"
```

## Docker Deployment

```bash
cd backend

# Build the image
docker build -t mentors-mantra-backend .

# Run the container
docker run -p 8000:8000 --env-file .env mentors-mantra-backend
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/health` | Detailed health status |
| POST | `/api/generate` | Generate test paper |
| GET | `/api/download/{filename}` | Download generated PDF |
| GET | `/api/models` | List available LLM models |

### Generate Test Paper

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Physics",
    "topic": "Electrostatics",
    "total_questions": 20
  }'
```

## Tech Stack

- **Frontend**: Next.js 14, Tailwind CSS, Lucide Icons
- **Backend**: FastAPI, Python 3.9+
- **AI**: LiteLLM (Gemini/OpenAI/Claude)
- **PDF**: pdflatex, Jinja2
- **Containerization**: Docker

## License

MIT
