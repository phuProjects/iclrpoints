# ICLR Points

Compare research areas by ICLR points (faculty-per-publication ratio normalized to Machine Learning).

## Setup
1. Install dependencies  
   `pip install -r requirements.txt`

2. Run the API  
   `uvicorn backend.iclr_api:app --host 0.0.0.0 --port 8001 --reload`

3. Run the frontend  
   `cd frontend`  
   `python -m http.server 8000`  
   Open http://localhost:8000

## API
`GET /iclr_points?from_year=2019&to_year=2023`

## Data
Place in `data/`:
- csrankings_march.csv
- area.csv
- dblp.xml.gz
