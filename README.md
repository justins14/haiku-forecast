# Haiku Forecast

A hobby project weather application that displays the forecast as haikus.

## Development

This project uses a SvelteKit frontend and FastAPI backend. It was built mostly using Cursor AI as a test to see what it is capable of.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:5173

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000 


Uses OpenStreetMap Nominatim API for geocoding and weather data from the Open-Meteo API.
Haikus were generated primarily by ChatGPT with some modifications.