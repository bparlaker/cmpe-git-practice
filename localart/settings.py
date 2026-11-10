"""
Settings for my Local Art Archive project.

I read most of the secret or server specific values from environment
variables, so the same code works on my laptop, in Docker and on Render.
"""

import os
from pathlib import Path

import dj_database_url

# The folder that has manage.py in it.
BASE_DIR = Path(__file__).resolve().parent.parent

# On Render I set SECRET_KEY as an environment variable.
# The default here is only for running the project on my own computer.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")

# DEBUG is on unless I say "False" in the environment.
DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Render gives me the public host name in this variable, so I add it here.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
    CSRF_TRUSTED_ORIGINS = ["https://" + RENDER_HOST]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # My own app, everything about craft entries lives here.
    "archive",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves my CSS and JS files on Render without nginx.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "localart.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # I keep all my templates in one "templates" folder at the top.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "localart.wsgi.application"


# Database
# Locally I use SQLite because it needs no setup.
# On Render and in Docker, DATABASE_URL points to PostgreSQL.
DATABASES = {
    "default": dj_database_url.config(
        default="sqlite:///" + str(BASE_DIR / "db.sqlite3"),
        conn_max_age=600,
    )
}


# Django checks passwords with these rules and stores them hashed (NFR-3).
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True


# Static files (my CSS and JS)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
# On Render (DEBUG off) WhiteNoise compresses the files and adds a hash to the
# file names, so browsers can cache them. Locally I keep the simple storage,
# so I do not need to run collectstatic after every change.
if DEBUG:
    STATIC_BACKEND = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    STATIC_BACKEND = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": STATIC_BACKEND},
}

# Uploaded photos go into the "media" folder.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Images can be at most 5 MB (NFR-4).
MAX_IMAGE_SIZE = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Where Django sends people after login and logout.
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"
