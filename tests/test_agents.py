from decimal import Decimal

import pytest
from sourcepilot.agents import EvaluationAgent, ResearchAgent, ResearchExhaustedError
from sourcepilot.providers.types import ProductCandidate, SearchDocument


class OneResultSearch:
    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]:
        return [
            SearchDocument(
                title="Supplier page",
                url="https://supplier.example/product",
                content="A product page without extractable procurement data",
                provider="test",
            )
        ]


class FailingExtractionLLM:
    async def structured_output(self, messages, output_type):
        raise RuntimeError("provider rejected every extraction")


@pytest.mark.asyncio
async def test_total_extraction_failure_is_not_reported_as_success() -> None:
    agent = ResearchAgent(OneResultSearch(), FailingExtractionLLM(), max_rounds=1)

    with pytest.raises(ResearchExhaustedError, match="all 1 source extractions failed"):
        await agent.run(
            {
                "description": "Find 50 laptops",
                "quantity": 50,
                "currency": "AED",
                "delivery_location": "Sharjah, United Arab Emirates",
                "procurement_region": "UAE",
                "sourcing_regions": ["United Arab Emirates", "GCC"],
            },
        )


def test_unknown_quantity_cannot_satisfy_requested_quantity() -> None:
    candidate = ProductCandidate(
        supplier_name="Supplier",
        supplier_website="https://supplier.example",
        product_name="Laptop",
        unit_price=Decimal("1000"),
        currency="AED",
        available_quantity=None,
        availability="In stock",
        source_url="https://supplier.example/product",
    )

    result = EvaluationAgent().evaluate(
        [candidate], {str(candidate.source_url): "verified"}, quantity=50, currency="AED"
    )

    assert result[0]["qualifies"] is False
    assert result[0]["quantity_status"] == "unconfirmed"


def test_offer_in_another_currency_cannot_qualify_without_conversion() -> None:
    candidate = ProductCandidate(
        supplier_name="GCC Supplier",
        supplier_website="https://supplier.example",
        product_name="Laptop",
        unit_price=Decimal("5500"),
        currency="SAR",
        available_quantity=50,
        source_url="https://supplier.example/product",
    )

    result = EvaluationAgent().evaluate(
        [candidate], {str(candidate.source_url): "verified"}, quantity=50, currency="AED"
    )

    assert result[0]["qualifies"] is False
    assert result[0]["currency_status"] == "mismatch"
