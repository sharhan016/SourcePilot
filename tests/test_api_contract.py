import pytest


@pytest.mark.asyncio
async def test_request_creation_returns_quickly_with_isolated_workflow(client) -> None:
    first = await client.post(
        "/api/v1/requests", json={"request": "Source 50 business laptops for Sharjah"}
    )
    second = await client.post(
        "/api/v1/requests", json={"request": "Source 100 wireless mice for Sharjah"}
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["workflow"]["id"] != second.json()["workflow"]["id"]
    assert first.json()["normalized_requirements"]["quantity"] == 50
    assert first.json()["normalized_requirements"]["currency"] == "AED"
    assert first.json()["normalized_requirements"]["procurement_region"] == "UAE"
    assert first.json()["normalized_requirements"]["sourcing_regions"] == [
        "United Arab Emirates",
        "GCC",
    ]
    assert first.json()["company_name"] == "IT Essentials (ITE)"
    assert first.json()["company_location"] == "Sharjah, United Arab Emirates"

    listed = await client.get("/api/v1/requests")
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_company_context_contract_exposes_configured_demo(client) -> None:
    response = await client.get("/api/v1/context")

    assert response.status_code == 200
    assert response.json() == {
        "company_name": "IT Essentials (ITE)",
        "company_location": "Sharjah, United Arab Emirates",
        "country": "United Arab Emirates",
        "currency": "AED",
        "procurement_region": "UAE",
        "sourcing_regions": ["United Arab Emirates", "GCC"],
    }


@pytest.mark.asyncio
async def test_validation_and_missing_resource_contract(client) -> None:
    invalid = await client.post("/api/v1/requests", json={"request": "short"})
    missing = await client.get("/api/v1/requests/not-a-real-id")
    assert invalid.status_code == 422
    assert missing.status_code == 404
