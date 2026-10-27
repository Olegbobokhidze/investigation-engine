from fastapi import APIRouter

from investigation_engine.api.dependencies import (
    InvestigationQuotaDependency,
    InvestigatorDependency,
)
from investigation_engine.api.schemas.investigations import (
    CreateInvestigationRequest,
    InvestigationResponse,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("")
async def create_investigation(
    body: CreateInvestigationRequest,
    investigator: InvestigatorDependency,
    # After the investigator, so a request the app can't serve (no LLM key) isn't counted.
    _quota: InvestigationQuotaDependency,
) -> InvestigationResponse:
    """Answers a question from the documents, with citations, or abstains."""
    investigation = await investigator.investigate(body.question)
    return InvestigationResponse.model_validate(investigation)
