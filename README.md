# Dad's Carb App

Small **Python/Flask** app to log meals and track daily carbohydrate intake with a rolling **7-day average**. Built for my dad (diabetes).

## Live Demo
https://kjohn314.pythonanywhere.com

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

## Tech
Python • Flask • Requests • HTML/CSS

## Structure
- `app/` (routes, templates, static)
- `run.py` (entry point)
- `requirements.txt`
