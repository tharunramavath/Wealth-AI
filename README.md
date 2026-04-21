# Financial Intelligence & Next Best Action (NBA) Platform

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![React](https://img.shields.io/badge/React-19-61dafb)

## 🔗 Live Demo

**Frontend**: https://wealth-ai-zzfq.vercel.app/

---

An institutional-grade wealth management platform that combines quantitative finance with generative AI to provide personalized investment strategies and real-time market intelligence.

## 🏗️ Architecture

```mermaid
graph TD
    subgraph Frontend_React
        UI[React UI - Vite]
        State[Context/Hooks]
    end

    subgraph Backend_FastAPI
        API[FastAPI Router]
        NBA[NBA Engine]
        Risk[Risk & Analytics]
        Chat[Chat Engine]
    end

    subgraph Intelligence_Layer
        NVIDIA_LLM[NVIDIA NIM: Llama 3.1 405B]
        NVIDIA_EMBED[NVIDIA Embeddings]
        FAISS[FAISS Vector Store]
    end

    subgraph Data_Layer
        DB[(SQLite: platform.db)]
        MKT_DB[(SQLite: market_data.db)]
        YF[yfinance API]
        NEWS[SERP News API]
    end

    %% Interactions
    UI <--> State
    State <--> API
    
    API <--> NBA
    API <--> Risk
    API <--> Chat

    Chat <--> NVIDIA_EMBED
    NVIDIA_EMBED <--> FAISS
    Chat <--> NVIDIA_LLM

    NBA --> DB
    Risk --> MKT_DB
    NBA <--> YF
    NBA <--> NEWS
```

## 🚀 Key Features

- **AI Advisor Chat**: RAG-based assistant powered by NVIDIA NIM (Llama 3.1) for deep market analysis and portfolio-specific queries.
- **NBA Engine**: "Next Best Action" recommendation system that triggers buy/sell/hold suggestions based on market events and user risk profiles.
- **Portfolio Analytics**: Real-time tracking, correlation matrices, and sector exposure heatmaps.
- **Risk Management**: Monte Carlo simulations, stress testing, and GARCH/Prophet-based forecasting.
- **Market Intelligence**: Automated news classification and sector rotation tracking (Leading, Lagging, Improving, Weakening).
- **Onboarding**: Dynamic risk tolerance assessment and goal-based investment planning.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python), SQLite, FAISS (Vector DB)
- **Frontend**: React 19, Tailwind CSS, Vite, Recharts
- **AI/ML**: NVIDIA Cloud APIs, LangChain, OpenAI API
- **Data**: yfinance, Feedparser, Pandas, Scikit-learn

## 📦 Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js & npm
- NVIDIA API Key

### Backend Setup
1. Clone the repository.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Set up your `.env` file (see `.env.example`).
6. Run the server: `uvicorn backend.main:app --reload`

### Frontend Setup
1. Navigate to the frontend folder: `cd frontend`
2. Install dependencies: `npm install`
3. Start the development server: `npm run dev`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
