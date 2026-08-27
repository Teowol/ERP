import sentry_sdk


class SentryModuleTagMiddleware:
    """Her isteğin URL'sine göre Sentry etiketi (module) atar."""

    MODULE_PREFIXES = {
        "inventory": "inventory",
        "catalog": "catalog",
        "procurement": "procurement",
        "production": "production",
        "quality": "quality",
        "distribution": "distribution",
        "logistics": "logistics",
        "core": "core",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        module = "other"
        path = request.path_info.strip("/").split("/")
        if path:
            first_segment = path[0]
            module = self.MODULE_PREFIXES.get(first_segment, "other")

        sentry_sdk.set_tag("module", module)
        sentry_sdk.set_tag("environment", "production")

        if request.user.is_authenticated:
            sentry_sdk.set_user({
                "id": str(request.user.id),
                "username": request.user.username,
                "ip_address": request.META.get("REMOTE_ADDR"),
            })

        response = self.get_response(request)
        return response