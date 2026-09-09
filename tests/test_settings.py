import pytest
from pydantic import ValidationError

from app.main import create_app
from app.settings import Settings


@pytest.mark.parametrize(
    "missing",
    [
        "github_app_id",
        "github_app_private_key",
        "github_installation_id",
        "github_managed_org",
        "github_template_repo",
    ],
)
async def test_missing_setting_fails_at_startup(settings, monkeypatch, missing):
    for name, value in settings.model_dump().items():
        if name == missing:
            monkeypatch.delenv(name.upper(), raising=False)
        else:
            if name == "github_app_private_key":
                value = value.get_secret_value()
            monkeypatch.setenv(name.upper(), str(value))
    app = create_app()
    with pytest.raises(ValidationError):
        async with app.router.lifespan_context(app):
            pytest.fail("Startup must fail")


def test_escaped_pem_and_default_url(settings, private_key, monkeypatch):
    monkeypatch.delenv("FLOO_API_URL", raising=False)
    values = settings.model_dump(exclude={"floo_api_url", "github_app_private_key"})
    parsed = Settings(**values, github_app_private_key=private_key.replace("\n", "\\n"))
    assert parsed.github_app_private_key.get_secret_value() == private_key
    assert str(parsed.floo_api_url) == "https://api.getfloo.com/"


def test_invalid_private_key_is_not_disclosed(settings):
    values = settings.model_dump(exclude={"github_app_private_key"})
    with pytest.raises(ValidationError) as exc:
        Settings(**values, github_app_private_key="secret-invalid-key")
    assert "secret-invalid-key" not in str(exc.value)
