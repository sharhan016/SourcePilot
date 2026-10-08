"""Playwright coverage for the persisted AI procurement workspace."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def request(request_id: str, text: str, status: str, stage: str, error=None):
    return {
        "id": request_id,
        "original_request": text,
        "normalized_requirements": {"quantity": 25, "category": "laptop"},
        "status": status,
        "company_name": "IT Essentials (ITE)",
        "company_location": "Sharjah, United Arab Emirates",
        "created_at": "2026-10-08T08:00:00Z",
        "updated_at": "2026-10-08T08:05:00Z",
        "workflow": {
            "id": f"workflow-{request_id}",
            "status": status,
            "current_stage": stage,
            "started_at": "2026-10-08T08:00:01Z",
            "completed_at": "2026-10-08T08:05:00Z" if status == "completed" else None,
            "error": error,
        },
    }


COMPLETED = request(
    "complete",
    "Source 25 business laptops with UAE warranty and delivery.",
    "completed",
    "review",
)
RUNNING = request(
    "running",
    "Find 12 monitors for the Sharjah operations team.",
    "running",
    "verification",
)
FAILED = request(
    "failed",
    "Source 8 network switches for the UAE office.",
    "failed",
    "verification",
    "Provider timed out after partial research",
)
NEW = request(
    "new",
    "Source 20 docking stations with UAE delivery.",
    "queued",
    "queued",
)


def product(product_id: str, supplier: str, *, verified=True, complete=True):
    return {
        "id": product_id,
        "name": "BusinessBook 14 Pro",
        "manufacturer": "Example",
        "model": "BB14",
        "specifications": {},
        "unit_price": "4200.00" if complete else None,
        "currency": "AED" if complete else None,
        "available_quantity": 40,
        "availability": "In stock",
        "warranty": "Three years" if complete else None,
        "delivery": "5 business days" if complete else None,
        "source_url": f"https://{supplier.lower()}.example/{product_id}",
        "verification_status": "verified" if verified else "extracted",
    }


def supplier(supplier_id: str, name: str, item: dict):
    return {
        "id": supplier_id,
        "name": name,
        "website": f"https://{name.lower()}.example",
        "location": "Dubai, UAE",
        "supplier_type": "authorized reseller",
        "verification_status": item["verification_status"],
        "products": [item],
    }


verified_product = product("product-1", "Alpha")
COMPLETED_DETAIL = {
    **COMPLETED,
    "suppliers": [supplier("supplier-1", "Alpha", verified_product)],
    "recommendation": {
        "id": "recommendation-1",
        "selected_options": [{"source_url": verified_product["source_url"]}],
        "evaluation_results": [
            {
                "supplier": "Alpha",
                "product": verified_product["name"],
                "source_url": verified_product["source_url"],
                "verification_status": "verified",
                "qualifies": True,
                "unit_price": "4200.00",
                "total_cost": "105000.00",
                "currency": "AED",
                "availability": "In stock",
                "warranty": "Three years",
                "delivery": "5 business days",
            }
        ],
        "total_cost": "105000.00",
        "currency": "AED",
        "reasoning_summary": (
            "Recommend Alpha: verified stock, UAE warranty, and the lowest comparable total."
        ),
        "evidence_references": [verified_product["source_url"]],
        "status": "ready",
        "review_note": None,
    },
}

RUNNING_DETAIL = {
    **RUNNING,
    "suppliers": [
        supplier("supplier-2", "Beta", product("product-2", "Beta", verified=False)),
        supplier(
            "supplier-3",
            "Gamma",
            product("product-3", "Gamma", verified=False, complete=False),
        ),
    ],
    "recommendation": None,
}

FAILED_DETAIL = {
    **FAILED,
    "suppliers": [
        supplier(
            "supplier-4",
            "Delta",
            product("product-4", "Delta", verified=False, complete=False),
        )
    ],
    "recommendation": None,
}

NEW_DETAIL = {**NEW, "suppliers": [], "recommendation": None}


def execution(summary: dict, statuses: tuple[str, str, str, str], events: list[dict]):
    return {
        "workflow": summary["workflow"],
        "tasks": [
            {
                "id": f"{summary['id']}-task-{index}",
                "agent_type": agent,
                "task_type": f"{agent}_procurement",
                "status": status,
                "dependencies": [],
                "retry_count": 0,
                "error": summary["workflow"]["error"] if status == "failed" else None,
                "started_at": "2026-10-08T08:00:00Z" if status != "queued" else None,
                "completed_at": "2026-10-08T08:01:00Z" if status == "completed" else None,
            }
            for index, (agent, status) in enumerate(
                zip(
                    ("research", "verification", "evaluation", "recommendation"),
                    statuses,
                    strict=True,
                )
            )
        ],
        "events": events,
    }


def event(event_id: str, agent: str, event_type: str, status: str, metadata=None):
    return {
        "id": event_id,
        "task_id": f"task-{agent}",
        "agent": agent,
        "event_type": event_type,
        "capability": None,
        "provider": None,
        "status": status,
        "duration_ms": None,
        "metadata_json": metadata or {},
        "timestamp": "2026-10-08T08:01:00Z",
    }


EXECUTIONS = {
    "workflow-complete": execution(
        COMPLETED,
        ("completed", "completed", "completed", "completed"),
        [event("event-1", "evaluation", "task_completed", "completed", {"compared": 1})],
    ),
    "workflow-running": execution(
        RUNNING,
        ("completed", "running", "queued", "queued"),
        [event("event-2", "research", "task_completed", "completed", {"candidates": 2})],
    ),
    "workflow-failed": execution(
        FAILED,
        ("completed", "failed", "queued", "queued"),
        [event("event-3", "research", "task_completed", "completed", {"candidates": 1})],
    ),
    "workflow-new": execution(NEW, ("queued", "queued", "queued", "queued"), []),
}


def run() -> None:
    output = Path("/tmp/sourcepilot-browser")
    output.mkdir(exist_ok=True)
    posts = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors: list[str] = []
        page.on(
            "console",
            lambda message: errors.append(message.text) if message.type == "error" else None,
        )

        def route_api(route) -> None:
            url = route.request.url
            if url.endswith("/context"):
                body = {
                    "company_name": "IT Essentials (ITE)",
                    "company_location": "Sharjah, United Arab Emirates",
                    "country": "United Arab Emirates",
                    "currency": "AED",
                    "procurement_region": "UAE",
                    "sourcing_regions": ["United Arab Emirates", "GCC"],
                }
            elif url.endswith("/requests") and route.request.method == "GET":
                body = [NEW, RUNNING, COMPLETED, FAILED] if posts else [RUNNING, COMPLETED, FAILED]
            elif url.endswith("/requests") and route.request.method == "POST":
                posts.append(json.loads(route.request.post_data or "{}"))
                body = NEW
            elif "/recommendation/review" in url:
                body = {**COMPLETED_DETAIL["recommendation"], "status": "approved"}
            elif url.endswith("/requests/complete"):
                body = COMPLETED_DETAIL
            elif url.endswith("/requests/running"):
                body = RUNNING_DETAIL
            elif url.endswith("/requests/failed"):
                body = FAILED_DETAIL
            elif url.endswith("/requests/new"):
                body = NEW_DETAIL
            elif "/workflows/" in url:
                workflow_id = url.rsplit("/", 1)[-1]
                body = EXECUTIONS[workflow_id]
            else:
                body = {}
            route.fulfill(status=200, content_type="application/json", body=json.dumps(body))

        page.route("**/api/v1/**", route_api)

        # Initial screen and compact history.
        page.goto("http://127.0.0.1:5173", wait_until="networkidle")
        expect(page.get_by_placeholder("What are you looking for?")).to_be_visible()
        expect(page.locator(".company-corner").get_by_text("IT Essentials (ITE)")).to_be_visible()
        page.screenshot(path=str(output / "initial.png"), full_page=True)
        page.get_by_role("button", name="Open request history").click()
        expect(page.get_by_role("link", name="New request")).to_be_visible()
        expect(page.get_by_role("navigation", name="Previous procurement requests")).to_be_visible()
        page.wait_for_timeout(350)
        page.screenshot(path=str(output / "initial-sidebar.png"), full_page=True)

        # Opening persisted history never creates a workflow.
        page.get_by_role("link", name=COMPLETED["original_request"]).click()
        page.wait_for_url("**/requests/complete")
        assert len(posts) == 0
        expect(page.get_by_text("Recommendation ready")).to_be_visible()
        expect(page.get_by_role("heading", name="Supplier comparison")).to_be_visible()
        expect(page.get_by_text("Estimated total")).to_be_visible()
        page.get_by_text("Execution details").click()
        expect(page.get_by_text("Completed handoff")).to_be_visible()
        page.screenshot(path=str(output / "completed.png"), full_page=True)

        # Live and parallel workflow state comes from persisted task data.
        page.goto("http://127.0.0.1:5173/requests/running", wait_until="networkidle")
        expect(page.get_by_text("Verification agent is working")).to_be_visible()
        expect(page.get_by_text("2 suppliers in parallel verification")).to_be_visible()
        expect(page.get_by_text("Verifying supplier information…")).to_be_visible()
        page.screenshot(path=str(output / "running.png"), full_page=True)

        # Partial results remain inspectable after a failure.
        page.goto("http://127.0.0.1:5173/requests/failed", wait_until="networkidle")
        expect(page.get_by_text("This run needs attention.")).to_be_visible()
        expect(page.get_by_text("Delta")).to_be_visible()
        page.screenshot(path=str(output / "partial-error.png"), full_page=True)

        # Starting another request remains available and creates one independent run.
        page.get_by_placeholder("What are you looking for?").fill(NEW["original_request"])
        page.get_by_role("button", name="Send procurement request").click()
        page.wait_for_url("**/requests/new")
        assert len(posts) == 1
        expect(page.get_by_text("Request queued")).to_be_visible()

        # Mobile layout and overlay sidebar.
        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.route("**/api/v1/**", route_api)
        mobile.goto("http://127.0.0.1:5173", wait_until="networkidle")
        expect(mobile.get_by_placeholder("What are you looking for?")).to_be_visible()
        mobile.get_by_role("button", name="Open request history").click()
        expect(
            mobile.get_by_role("navigation", name="Previous procurement requests")
        ).to_be_visible()
        expect(mobile.get_by_role("link", name="New request")).to_be_visible()
        mobile.wait_for_timeout(350)
        mobile.screenshot(path=str(output / "mobile-sidebar.png"), full_page=True)
        assert mobile.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    run()
