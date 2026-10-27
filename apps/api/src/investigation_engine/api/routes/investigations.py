from fastapi import APIRouter

from investigation_engine.api.dependencies import InvestigatorDependency
from investigation_engine.api.schemas.investigations import (
    CreateInvestigationRequest,
    InvestigationResponse,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("")
async def create_investigation(
    body: CreateInvestigationRequest, investigator: InvestigatorDependency
) -> InvestigationResponse:
    """Answers a question from the documents, with citations, or abstains."""
    investigation = await investigator.investigate(body.question)
    return InvestigationResponse.model_validate(investigation)
