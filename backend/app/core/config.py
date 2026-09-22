from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"
    llm_api_key: str = ""

    max_agent_steps: int = 30
    max_action_retries: int = 3

    allow_external_navigation: bool = False
    allowed_domains: str = "localhost,127.0.0.1"

    require_confirmation_for_sensitive_actions: bool = True

    enable_ocr: bool = True
    enable_presidio: bool = False

    ocr_cache: bool = True
    perception_cache: bool = True

    log_level: str = "INFO"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    test_sites_port: int = 3000

    headless_browser: bool = False
    playwright_slow_mo: int = 50

    @property
    def allowed_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_domains.split(",") if d.strip()]


settings = Settings()
