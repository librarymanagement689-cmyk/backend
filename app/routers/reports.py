from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.services.report_service import ReportService
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Reports"])

@router.get("/dashboard")
async def get_dashboard_summary(
    current_admin: dict = Depends(get_current_admin)
):
    """
    Returns dynamically calculated library metrics: total/available/borrowed/published books,
    total members, active/overdue orders, today's orders count, today's collection, monthly collection.
    """
    return await ReportService.get_dashboard_stats()

@router.get("/reports/daily")
async def get_daily_report(
    date: Optional[str] = Query(None, description="Format YYYY-MM-DD. Defaults to today."),
    current_admin: dict = Depends(get_current_admin)
):
    return await ReportService.get_daily_report(report_date=date)

@router.get("/reports/monthly")
async def get_monthly_report(
    month: Optional[str] = Query(None, description="Format YYYY-MM. Defaults to current month."),
    current_admin: dict = Depends(get_current_admin)
):
    return await ReportService.get_monthly_report(year_month=month)

@router.get("/reports/book/{book_id}")
async def get_book_report(
    book_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    return await ReportService.get_book_collection_report(book_id=book_id)
