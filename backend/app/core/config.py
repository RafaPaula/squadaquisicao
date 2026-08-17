from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str = "postgresql+psycopg2://at_user:at_password@localhost:5432/talent_db"

    # auth.inhire.app cuida do login; api.inhire.app serve os dados.
    # Confirmado contra a documentacao oficial (POST /login, POST
    # /job-talents/{jobId}/talents/paginated/lean).
    INHIRE_AUTH_BASE_URL: str = "https://auth.inhire.app"
    INHIRE_API_BASE_URL: str = "https://api.inhire.app"
    INHIRE_EMAIL: str = ""
    INHIRE_PASSWORD: str = ""
    # Identificador do tenant, obrigatorio no header X-Tenant em toda chamada
    # (tanto no login quanto na api). Ex.: "acme-corp".
    INHIRE_TENANT: str = ""
    INHIRE_LOGIN_ENDPOINT: str = "/login"
    INHIRE_JOBS_ENDPOINT: str = "/jobs/paginated/lean"

    # Board de funil de vagas (Aquisicao de Talentos), hoje atualizado
    # manualmente pela recrutadora - Fase 4 (leitura por enquanto).
    AZURE_DEVOPS_ORG_URL: str = ""
    AZURE_DEVOPS_PROJECT: str = ""
    AZURE_DEVOPS_TEAM: str = ""
    AZURE_DEVOPS_PAT: str = ""

    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "./data/resumes"
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "resumes"

    # Origens liberadas no CORS, separadas por virgula. Em producao aponta
    # pro dominio do frontend publicado (ex.: Vercel).
    CORS_ORIGINS: str = "http://localhost:5173"

    # Gate de senha temporario enquanto o SSO real (Entra ID) nao sai do
    # papel — ver memoria "project_talent_mirror_sso_pending". Vazio =
    # desligado (uso local). Setado = toda rota (exceto /health) exige o
    # header `X-App-Password` com esse valor.
    APP_ACCESS_PASSWORD: str = ""


settings = Settings()
