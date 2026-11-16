"""
Configurações do projeto Vagas Litoral Sul.

Os valores sensíveis ou que mudam entre desenvolvimento e produção vêm de
variáveis de ambiente (ou do arquivo .env). Veja o arquivo .env.example.
"""

from pathlib import Path

from django.contrib.messages import constants as mensagens
from django.core.exceptions import ImproperlyConfigured

from . import env

# Pasta raiz do projeto (onde fica o manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o arquivo .env, se existir
env.carregar_env(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Segurança básica
# ---------------------------------------------------------------------------

DEBUG = env.booleano("DEBUG", False)

SECRET_KEY = env.texto("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Só aceitamos uma chave fixa em desenvolvimento
        SECRET_KEY = "chave-insegura-apenas-para-desenvolvimento"
    else:
        raise ImproperlyConfigured(
            "Defina a variável SECRET_KEY no ambiente ou no arquivo .env."
        )

ALLOWED_HOSTS = env.lista("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Origens confiáveis para o CSRF (ex.: https://canguaretama.ifrn.edu.br)
CSRF_TRUSTED_ORIGINS = env.lista("CSRF_TRUSTED_ORIGINS")


# ---------------------------------------------------------------------------
# Aplicações
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps do projeto
    "vagas.apps.VagasConfig",
    "prefeituras.apps.PrefeiturasConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # Proteção contra clickjacking em todo o site (exceto no widget)
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# ---------------------------------------------------------------------------
# Banco de dados (SQLite)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Senhas (somente o sistema do Django guarda e valida senhas)
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Idioma, fuso horário e datas
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Recife"
USE_I18N = True
USE_TZ = True

# Aceita e exibe números no padrão brasileiro (ex.: salário 1.518,00)
USE_THOUSAND_SEPARATOR = True


# ---------------------------------------------------------------------------
# Publicação sob subcaminho (ex.: https://dominio/vagas/)
# ---------------------------------------------------------------------------

# Prefixo do site. Deixe vazio em desenvolvimento; em produção use "/vagas".
# A barra final é removida para evitar endereços com "//".
FORCE_SCRIPT_NAME = env.texto("FORCE_SCRIPT_NAME").rstrip("/") or None

# Um STATIC_URL relativo ("static/") recebe o prefixo automaticamente.
STATIC_URL = env.texto("STATIC_URL", "static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"  # destino do collectstatic

# Pode ser um nome de rota ("prefeituras:entrar") ou um caminho
LOGIN_URL = env.texto("LOGIN_URL", "prefeituras:entrar")
LOGIN_REDIRECT_URL = "prefeituras:painel"
LOGOUT_REDIRECT_URL = "vagas:inicio"

# Cookies com nome e caminho próprios, para não colidir com outros
# sistemas publicados no mesmo domínio do IFRN.
SESSION_COOKIE_NAME = "vls_sessionid"
CSRF_COOKIE_NAME = "vls_csrftoken"
SESSION_COOKIE_PATH = (FORCE_SCRIPT_NAME or "") + "/"
CSRF_COOKIE_PATH = SESSION_COOKIE_PATH


# ---------------------------------------------------------------------------
# Cabeçalhos de segurança
# ---------------------------------------------------------------------------

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Sites autorizados a exibir o widget em <iframe>.
# Exemplo: 'self' https://portal.ifrn.edu.br
WIDGET_FRAME_ANCESTORS = env.texto("WIDGET_FRAME_ANCESTORS", "'self'")


# ---------------------------------------------------------------------------
# Regras do sistema
# ---------------------------------------------------------------------------

# Quantas solicitações de vaga um mesmo IP pode enviar por hora
LIMITE_SOLICITACOES_POR_HORA = env.inteiro("LIMITE_SOLICITACOES_POR_HORA", 5)

# Ligue (True) somente quando o Django estiver atrás do Nginx configurado
# para enviar o cabeçalho X-Real-IP (ver README). Sem isso, todos os
# visitantes pareceriam ter o IP do próprio Nginx.
CONFIAR_PROXY_REVERSO = env.booleano("CONFIAR_PROXY_REVERSO", False)

# Após quantos dias os dados de contato de solicitações recusadas são apagados
DIAS_PARA_ANONIMIZAR_RECUSADAS = 180


# ---------------------------------------------------------------------------
# Mensagens (classes CSS em português)
# ---------------------------------------------------------------------------

MESSAGE_TAGS = {
    mensagens.DEBUG: "info",
    mensagens.INFO: "info",
    mensagens.SUCCESS: "sucesso",
    mensagens.WARNING: "aviso",
    mensagens.ERROR: "erro",
}


# ---------------------------------------------------------------------------
# Produção (HTTPS) - descomente ao publicar com certificado
# ---------------------------------------------------------------------------

# O Nginx informa ao Django que a conexão original era HTTPS:
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
#
# Redireciona HTTP para HTTPS (pode ser feito também no Nginx):
# SECURE_SSL_REDIRECT = True
#
# Cookies de sessão e CSRF só trafegam por HTTPS:
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
#
# HSTS: o navegador passa a usar sempre HTTPS. Comece com um valor baixo
# (ex.: 3600) e aumente depois de confirmar que tudo funciona.
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = False
# SECURE_HSTS_PRELOAD = False
