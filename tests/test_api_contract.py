import pytest


@pytest.mark.asyncio
async def test_request_creation_returns_quickly_with_isolated_workflow(client) -> None:
    first = await client.post("/api/v1/requests", json={"request": "Find 50 MacBook Pro laptops"})
    second = await client.post("/api/v1/requests", json={"request": "Find 100 wireless mice"})

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["workflow"]["id"] != second.json()["workflow"]["id"]
    assert first.json()["normalized_requirements"]["quantity"] == 50

    listed = await client.get("/api/v1/requests")
    assert listed.status_code == 200
    assert len(listed.json()) == 2


@pytest.mark.asyncio
async def test_validation_and_missing_resource_contract(client) -> None:
    invalid = await client.post("/api/v1/requests", json={"request": "short"})
    missing = await client.get("/api/v1/requests/not-a-real-id")
    assert invalid.status_code == 422
    assert missing.status_code == 404
