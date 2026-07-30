# HydroShield — Backend API

FastAPI backend server for the HydroShield AI-Powered Flood Management System.

---

## 🛠 Local Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in required MongoDB, Gemini, OpenWeather, and Resend API keys.

3. **Start Development Server**:
   ```bash
   python main.py
   ```
   or
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The API will be available on `http://localhost:8000` and interactive docs on `http://localhost:8000/docs`.

---

## 🚀 Deployment Instructions

### Deploy to Render (Recommended Web Service)
1. Create a new **Web Service** on Render.
2. Select your repository and set **Root Directory** to `backend`.
3. Environment: `Python 3`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables from `backend/.env`.

### Deploy using Docker
```bash
docker build -t hydroshield-backend .
docker run -p 8000:8000 --env-file .env hydroshield-backend
```
