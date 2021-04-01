from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "opsgrid.core"

    def ready(self):
        from . import signals  # noqa
