# -* encoding: utf-8 *-
import django

from .apps import DjangoIntegration, monkeypatch_django, post_reconnect, pre_reconnect

__all__ = [pre_reconnect, post_reconnect, monkeypatch_django, DjangoIntegration]

if django.VERSION < (3, 2):
    default_app_config = "django_dbconn_retry.DjangoIntegration"
