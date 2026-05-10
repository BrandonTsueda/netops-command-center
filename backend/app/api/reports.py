from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reports import MorningReport
from app.services.report_service import generate_morning_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/morning", response_model=MorningReport)
async def morning_report(include_ai: bool = False, db: Session = Depends(get_db)) -> MorningReport:
    return await generate_morning_report(db=db, include_ai=include_ai)


@router.get("/morning.md", response_class=PlainTextResponse)
async def morning_report_markdown(include_ai: bool = False, db: Session = Depends(get_db)) -> str:
    report = await generate_morning_report(db=db, include_ai=include_ai)
    if report.ai_summary:
        return f"{report.markdown}\n\n## AI Summary\n\n{report.ai_summary}\n"
    return report.markdown
