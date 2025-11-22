# Dad's Carb App

Small **Python/Flask** app to log meals and track daily carbohydrate intake with a rolling **7-day average**. Built for my dad (diabetes).

## Live Demo
Coming soon on GitHub Pages (static landing). The Flask API needs a server host (e.g., Render/Fly/Railway); see Deploy section.

## Features
- Natural-language meal logging via **Nutritionix API**
- Daily total + 7-day average
- Cookie-based tracking (no login), history with undo/delete/clear
- Optional voice input (browser dependent)

## Run Locally (simple)
1) Install dependencies: `pip install -r requirements.txt`  
2) Set two env vars (from your Nutritionix account):  
   - `NUTRITIONIX_APP_ID=your_app_id`  
   - `NUTRITIONIX_API_KEY=your_api_key`  
3) Start the app: `python run.py`  
4) Open the URL Flask prints (usually http://127.0.0.1:5000)

## Deploy
GitHub Pages is static-only, so you'll still need a small server to run Flask. Quick option: Render free web service.

Render one-liner (from this repo root):
- Create a new "Web Service" → connect this repo → Environment: Python → Start command: `gunicorn -b 0.0.0.0:10000 run:app` → Add env vars `NUTRITIONIX_APP_ID` and `NUTRITIONIX_API_KEY` → deploy.

## Tech
Python • Flask • Requests • HTML/CSS

## Structure
- `app/` (routes, templates, static)
- `run.py` (entry point)
- `requirements.txt`
