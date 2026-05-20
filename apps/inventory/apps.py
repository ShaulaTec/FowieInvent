from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'apps.inventory'

    def ready(self):
        # Importamos las señales aquí para evitar problemas de importación circular
        import apps.inventory.signals