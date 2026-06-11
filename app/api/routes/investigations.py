from fastapi import APIRouter, Depends

from app.api.dependencies import get_investigation_agent
from app.api.schemas.api_responses import InvestigationRequest, InvestigationResponse

router = APIRouter(tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResponse)
def investigate(body: InvestigationRequest, agent=Depends(get_investigation_agent)) -> InvestigationResponse:
    result = agent.investigate(body.question)
    return InvestigationResponse(**result)
