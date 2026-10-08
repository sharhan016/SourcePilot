from sourcepilot.services import normalize_requirements


def test_normalizes_quantity_without_using_an_llm() -> None:
    normalized = normalize_requirements("Source 50 business laptops for the Sharjah office.")
    assert normalized["quantity"] == 50
    assert normalized["category"] == "laptop"


def test_unknown_values_are_not_invented() -> None:
    normalized = normalize_requirements("Find ergonomic chairs for the studio")
    assert normalized["quantity"] == 1
    assert "price" not in normalized
