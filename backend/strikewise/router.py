# strikewise/router.py
from fastapi import APIRouter
from strikewise.models import AnalysisRequest, AnalysisResponse
from strikewise.service import run_option_analysis

router = APIRouter()
@router.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalysisRequest):
    return run_option_analysis(request)

