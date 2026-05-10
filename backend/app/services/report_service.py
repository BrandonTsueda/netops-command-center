from app.core.time import utc_now
from app.schemas.reports import MorningReport
from app.services.ai_service import summarize_with_ollama
from app.services.dashboard_service import get_dashboard_summary
from sqlalchemy.orm import Session


async def generate_morning_report(db: Session, include_ai: bool = False) -> MorningReport:
    summary = get_dashboard_summary(db)
    generated_at = utc_now()

    lines = [
        "# Morning NOC Report",
        "",
        f"Generated at: {generated_at.isoformat()}",
        "",
        "## Fleet Summary",
        "",
        f"- Total devices: {summary.total_devices}",
        f"- Active devices: {summary.active_devices}",
        f"- Healthy: {summary.healthy}",
        f"- Warning: {summary.warning}",
        f"- Critical: {summary.critical}",
        f"- Unknown: {summary.unknown}",
        "",
        "## Device Status",
        "",
        "| Device | IP | Site | Role | Status | Last Check | Availability |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for device in summary.devices:
        last_check = device.last_check_at.isoformat() if device.last_check_at else "Never"
        lines.append(
            f"| {device.hostname} | {device.ip_address} | {device.site} | {device.role} | "
            f"{device.status} | {last_check} | {device.availability_percent}% |"
        )

    lines.extend(["", "## Failed Checks", ""])
    if summary.failed_checks:
        for check in summary.failed_checks[:10]:
            lines.append(f"- Device {check.device_id}: {check.check_type} `{check.target}` is {check.status}. {check.message}")
    else:
        lines.append("- No warning or critical checks recorded.")

    lines.extend(["", "## Recent Changes", ""])
    if summary.recent_drift:
        for event in summary.recent_drift[:10]:
            lines.append(f"- {event.severity.upper()}: {event.title} - {event.description}")
    else:
        lines.append("- No drift events recorded.")

    lines.extend(["", "## Recommended Actions", ""])
    if summary.critical:
        lines.append("- Prioritize critical devices and confirm whether failures are network, service, or host-level.")
    if summary.warning:
        lines.append("- Review warning devices for degraded services, intermittent reachability, or HTTP client errors.")
    if summary.unknown:
        lines.append("- Add active check targets for unknown devices so they can be classified.")
    if not any([summary.critical, summary.warning, summary.unknown]):
        lines.append("- Fleet is currently healthy based on recorded checks. Continue routine monitoring.")

    markdown = "\n".join(lines)
    ai_summary = await summarize_with_ollama(_build_ai_prompt(markdown)) if include_ai else None
    return MorningReport(generated_at=generated_at, markdown=markdown, ai_summary=ai_summary)


def _build_ai_prompt(report_markdown: str) -> str:
    return (
        "You are assisting a NOC engineer. Summarize this report in plain English. "
        "Focus on outages, likely impact, and next actions. Keep it concise.\n\n"
        f"{report_markdown}"
    )
