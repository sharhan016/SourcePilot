"""Manual Playwright smoke test used by the Vertex UI verification workflow."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright


REQUEST = {
    "id": "request-1",
    "original_request": "Find 50 MacBook Pro 14-inch laptops for the company.",
    "normalized_requirements": {"quantity": 50, "category": "laptop"},
    "status": "completed",
    "company_name": "Acme Operations",
    "company_location": "Bengaluru, India",
    "created_at": "2026-10-08T08:00:00Z",
    "updated_at": "2026-10-08T08:05:00Z",
    "workflow": {
        "id": "workflow-1",
        "status": "completed",
        "current_stage": "review",
        "started_at": "2026-10-08T08:00:01Z",
        "completed_at": "2026-10-08T08:05:00Z",
        "error": None,
    },
}

DETAIL = {
    **REQUEST,
    "suppliers": [
        {
            "id": "supplier-1",
            "name": "Verified Business Store",
            "website": "https://supplier.example",
            "location": "Bengaluru",
            "supplier_type": "authorized reseller",
            "verification_status": "verified",
            "products": [
                {
                    "id": "product-1",
                    "name": "MacBook Pro 14-inch",
                    "manufacturer": "Apple",
                    "model": "M-series",
                    "specifications": {},
                    "unit_price": "150000.00",
                    "currency": "INR",
                    "available_quantity": 75,
                    "availability": "In stock",
                    "warranty": "One year",
                    "delivery": "7 days",
                    "source_url": "https://supplier.example/product",
                    "verification_status": "verified",
                }
            ],
        }
    ],
    "recommendation": {
        "id": "recommendation-1",
        "selected_options": [],
        "evaluation_results": [],
        "total_cost": "7500000.00",
        "currency": "INR",
        "reasoning_summary": "Recommend the verified option with the lowest comparable total.",
        "evidence_references": ["https://supplier.example/product"],
        "status": "ready",
        "review_note": None,
    },
}

EXECUTION = {
    "workflow": REQUEST["workflow"],
    "tasks": [
        {
            "id": f"task-{index}",
            "agent_type": agent,
            "task_type": f"{agent}_procurement",
            "status": "completed",
            "dependencies": [],
            "retry_count": 0,
            "error": None,
            "started_at": "2026-10-08T08:00:00Z",
            "completed_at": "2026-10-08T08:01:00Z",
        }
        for index, agent in enumerate(("research", "verification", "evaluation", "recommendation"))
    ],
    "events": [],
}


def run() -> None:
    output = Path("/tmp/sourcepilot-browser")
    output.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)

        def route_api(route) -> None:
            url = route.request.url
            if url.endswith("/requests") and route.request.method == "GET":
                body = [REQUEST]
            elif url.endswith("/requests") and route.request.method == "POST":
                body = {**REQUEST, "id": "request-2"}
            elif url.endswith("/requests/request-1"):
                body = DETAIL
            elif url.endswith("/workflows/workflow-1"):
                body = EXECUTION
            elif "/recommendation/review" in url:
                body = {**DETAIL["recommendation"], "status": "approved"}
            else:
                body = {}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

        page.route("**/api/v1/**", route_api)
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        assert page.get_by_role("heading", name="Turn a requirement into a defensible shortlist.").is_visible()
        assert page.get_by_text("Ready for review").is_visible()
        page.screenshot(path=str(output / "dashboard.png"), full_page=True)

        page.goto("http://127.0.0.1:5173/requests/request-1", wait_until="networkidle")
        assert page.get_by_text("Estimated total").is_visible()
        assert page.get_by_role("button", name="Approve shortlist").is_visible()
        page.screenshot(path=str(output / "details.png"), full_page=True)

        page.goto("http://127.0.0.1:5173/architecture", wait_until="networkidle")
        page.wait_for_selector(".mermaid-output svg")
        assert page.locator(".diagram-card").count() == 6
        page.screenshot(path=str(output / "architecture.png"), full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.route("**/api/v1/**", route_api)
        mobile.goto("http://127.0.0.1:5173", wait_until="networkidle")
        assert mobile.get_by_role("button", name="Start sourcing").is_visible()
        mobile.screenshot(path=str(output / "mobile.png"), full_page=True)
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    run()

