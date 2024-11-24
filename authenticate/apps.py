from django.apps import AppConfig

class AuthenticateConfig(AppConfig):
    name = 'authenticate'

    def ready(self):
        import authenticate.signals
