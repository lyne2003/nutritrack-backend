# NutriTrack Backend 🥗

A FastAPI-powered backend for NutriTrack — an AI-driven nutrition and health management system.

## 🚀 Features
- User authentication (signup/login)
- Dietary restriction & allergy tracking
- Lab result upload
- Ingredient recognition endpoints
- SQLAlchemy + MySQL database integration

## ⚙️ Setup Instructions
```bash
# Clone the repo
git clone https://github.com/lyne2003/nutritrack-backend.git
cd nutritrack-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload

# Tech Stack

# FastAPI
# SQLAlchemy
# MySQL / SQLite
# JWT Authentication