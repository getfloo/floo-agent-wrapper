from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, hide_input_in_errors=True)

    floo_api_url: AnyHttpUrl = AnyHttpUrl("https://api.getfloo.com")
    github_app_id: int = Field(gt=0)
    github_app_private_key: SecretStr
    github_installation_id: int = Field(gt=0)
    github_managed_org: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]*$")
    github_template_repo: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

    @field_validator("github_app_private_key")
    @classmethod
    def validate_key(cls, value: SecretStr) -> SecretStr:
        pem = value.get_secret_value().replace("\\n", "\n")
        try:
            key = serialization.load_pem_private_key(pem.encode(), password=None)
        except (ValueError, TypeError) as exc:
            raise ValueError("GITHUB_APP_PRIVATE_KEY must be an unencrypted RSA PEM") from exc
        if not isinstance(key, RSAPrivateKey):
            raise ValueError("GITHUB_APP_PRIVATE_KEY must be an RSA key")
        return SecretStr(pem)
