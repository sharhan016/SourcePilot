from sourcepilot.config import Settings


def test_default_company_context_is_uae_based_and_configurable(monkeypatch) -> None:
    settings = Settings(_env_file=None)
    assert settings.company_name == "IT Essentials (ITE)"
    assert settings.company_location == "Sharjah, United Arab Emirates"
    assert settings.company_country == "United Arab Emirates"
    assert settings.default_currency == "AED"
    assert settings.procurement_region == "UAE"
    assert settings.sourcing_regions == ["United Arab Emirates", "GCC"]

    monkeypatch.setenv("COMPANY_COUNTRY", "Oman")
    monkeypatch.setenv("DEFAULT_CURRENCY", "OMR")
    monkeypatch.setenv("SOURCING_REGIONS", "Oman,GCC")
    overridden = Settings(_env_file=None)
    assert overridden.company_country == "Oman"
    assert overridden.default_currency == "OMR"
    assert overridden.sourcing_regions == ["Oman", "GCC"]


def test_cors_origins_accept_comma_separated_environment_value(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_cors_origins_accept_json_environment_value(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173"]')
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["http://localhost:5173"]
