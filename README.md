# AI Tools Hub 🤖

A modern, open-source directory for discovering, comparing, and exploring AI tools. Find the right AI tool for your needs — with honest pricing info, free alternatives, and API details.

**🌐 Live Demo:** [ai-tools-hub-lilac-nu.vercel.app](https://ai-tools-hub-lilac-nu.vercel.app)

---

## ✨ Features

- **🔍 Search & Filter** — Find tools by name, category, or tags
- **💰 Pricing Transparency** — See free tiers, paid plans, and pricing links
- **🔄 Compare Tools** — Side-by-side comparison of multiple AI tools
- **🆓 Free Alternatives** — Discover free options for popular paid tools
- **🔗 API Reference** — Quick access to API docs, endpoints, and auth methods
- **📱 Responsive Design** — Works great on desktop and mobile

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React, Vite, Tailwind CSS |
| **Backend** | Python, FastAPI |
| **Database** | SQLite (JSON fallback) |
| **Deployment** | Vercel (frontend), Render (backend) |

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+

### 1. Clone the repo
```bash
git clone https://github.com/utkarshcodehub/ai-tools-hub.git
cd ai-tools-hub
```

### 2. Start the backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
Backend runs at `http://localhost:8000`

### 3. Start the frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`

---

## 📁 Project Structure

```
ai-tools-hub/
├── frontend/          # React + Vite app
│   ├── src/
│   │   ├── components/   # UI components
│   │   ├── pages/        # Page components
│   │   └── api/          # API client
│   └── package.json
│
├── backend/           # FastAPI server
│   ├── routes/          # API endpoints
│   ├── scrapers/        # Data collection tools
│   ├── main.py          # App entry point
│   └── requirements.txt
│
├── data/              # Tool data (JSON)
│   ├── tools.json       # All AI tools
│   └── categories.json  # Category definitions
│
└── render.yaml        # Render deployment config
```

---

## 🤖 Auto Data Collection

The project includes scrapers to automatically discover new AI tools from:

| Source | What it finds |
|--------|---------------|
| **Hacker News** | "Show HN" AI tool launches |
| **GitHub** | Trending AI repositories |
| **ProductHunt** | New AI product launches (API key required) |

### Run manually:
```bash
cd backend
python run_monitors.py --days 7 --save
```

### Run on schedule:
```bash
python scheduler.py
```

---

## 🔧 Environment Variables

### Frontend (`frontend/.env.local`)
```env
VITE_API_BASE_URL=http://localhost:8000
```

### Backend (`backend/.env`)
```env
ALLOWED_ORIGINS=http://localhost:5173
# Optional:
PH_API_KEY=your_producthunt_key
GOOGLE_API_KEY=your_gemini_key
```

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tools` | List all tools |
| GET | `/tools/{id}` | Get tool by ID |
| GET | `/tools/free` | Tools with free tier |
| GET | `/tools/compare?ids=a,b` | Compare tools |
| GET | `/categories` | List categories |
| GET | `/search?q=query` | Search tools |

Full API docs at `/docs` when running locally.

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Add new AI tools to `data/tools.json`
- Improve the UI/UX
- Add new features
- Fix bugs

---

## 📝 License

MIT License — feel free to use this project for anything.

---

<p align="center">
  Made with ❤️ for the AI community
</p>
