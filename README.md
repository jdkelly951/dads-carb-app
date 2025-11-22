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

No keys? You can still use the **manual entry** form (carb grams you type) but API lookups/voice are disabled until the keys are set.

## Deploy
GitHub Pages is static-only, so you'll still need a small server to run Flask. Quick option: Render free web service.

Render deploy (few clicks):
- Create new "Web Service" → connect this repo → Environment: Python
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn -b 0.0.0.0:$PORT run:app`
- Add env vars `API_NINJAS_KEY` (for auto lookup/voice) and `DATABASE_URL` (from your Postgres provider, e.g., Neon). Nutritionix vars are not used.
- Plan: Free → deploy

Deploy button (Render):

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fjdkelly951%2Fdads-carb-app)

### Database (keeps history safe)
- In Render dashboard: New → PostgreSQL → Free → create.
- Copy the `External Database URL` (or click "Connect" on your service) and set it as `DATABASE_URL` env var on the web service.
- No migrations needed; the app creates the `food_logs` table automatically on boot.

### Nutrition API (auto lookup/voice)
- Using API Ninjas Nutrition endpoint (CalorieNinjas is being sunset). Get a free API key at api-ninjas.com and set `API_NINJAS_KEY` on your web service.
- Without this key, manual entry still works.

## Tech
Python • Flask • Requests • HTML/CSS

## Structure
- `app/` (routes, templates, static)
- `run.py` (entry point)
- `requirements.txt`
