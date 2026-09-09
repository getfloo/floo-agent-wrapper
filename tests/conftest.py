import httpx
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.main import create_app
from app.settings import Settings


@pytest.fixture(scope="session")
def private_key():
    return (
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        .decode()
    )


@pytest.fixture
def settings(private_key):
    return Settings(
        floo_api_url="https://floo.test",
        github_app_id=123,
        github_app_private_key=private_key,
        github_installation_id=456,
        github_managed_org="managed",
        github_template_repo="templates/starter",
    )


@pytest.fixture(autouse=True)
def upstream():
    # Any HTTPX call without a registered mock raises; real APIs cannot be reached.
    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        yield router


@pytest.fixture
async def client(settings):
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://wrapper.test",
            headers={"Authorization": "Bearer floo_test", "X-Floo-Org-Id": "org-test"},
        ) as client:
            yield client
