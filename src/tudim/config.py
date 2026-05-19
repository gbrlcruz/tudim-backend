from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    database_url: str | None = None
    gcp_project: str | None = None
    gemini_api_key: str | None = None

    public_base_url: str = ""


settings = Settings()
