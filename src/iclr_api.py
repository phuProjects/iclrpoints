from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.iclr_point import (
    CSRANKINGS_PATH, AREA_PATH,
    load_faculty_names, load_conference_to_area,
    compute_iclr_points_year_range,
)

app = FastAPI()

# ✅ CORS middleware so frontend (8000) can call backend (8001)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Load static data once at startup
faculty_set = load_faculty_names(CSRANKINGS_PATH)
conf_to_area, area_to_parent = load_conference_to_area(AREA_PATH)

@app.get("/iclr_points")
def iclr_points(from_year: int = 2019, to_year: int = 2023):
    # make sure order is sane
    if from_year > to_year:
        from_year, to_year = to_year, from_year

    try:
        rows = compute_iclr_points_year_range(
            from_year,
            to_year,
            faculty_set,
            conf_to_area,
            area_to_parent,
        )
    except ValueError as e:
        # e.g., Machine learning baseline missing
        raise HTTPException(status_code=400, detail=str(e))

    # FastAPI will serialize this list of dicts as JSON
    return JSONResponse(content=rows)
