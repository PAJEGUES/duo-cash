CATEGORIES = (
    "ALIMENTACAO",
    "SAUDE",
    "TRANSPORTE",
    "EDUCACAO",
    "LAZER",
    "INVESTIMENTOS",
    "DIVIDAS",
    "AGUA_LUZ",
    "INTERNET_PESSOAL",
    "INTERNET_CASA",
    "TAXA_INCC",
    "TAXA_EVOLUCAO_OBRA",
    "TAXAS_INESPERADAS",
    "PET",
    "GASTO_DESNECESSARIO",
    "COMPRAS_ONLINE",
    "BOLETOS",
)

ICON_KEYS = (
    "cinema",
    "restaurante",
    "bar",
    "viagem",
    "show",
    "jogos",
    "streaming",
    "esportes",
    "festa",
    "praia",
    "museu",
    "passeio",
)

OWNER = "OWNER"
EDITOR = "EDITOR"
VIEWER = "VIEWER"
ROLES = (OWNER, EDITOR, VIEWER)
INVITE_ROLES = (EDITOR, VIEWER)
WRITE_ROLES = (OWNER, EDITOR)

MAX_AMOUNT_CENTS = 10_000_000_000
MAX_DESCRIPTION = 100
MAX_WORKSPACE_NAME = 60
MAX_ICON = 16
DEFAULT_WORKSPACE_ICON = "🏠"
