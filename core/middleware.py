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

        if hasattr(request, "user") and request.user.is_authenticated:
            sentry_sdk.set_user({
                "id": str(request.user.id),
                "username": request.user.username,
                "ip_address": request.META.get("REMOTE_ADDR"),
            })

        response = self.get_response(request)
        return response

class EnglishResponseTranslationMiddleware:
    """Translate legacy hard-coded application text for English requests."""

    TRANSLATABLE_CONTENT_TYPES = ("text/html", "application/json", "text/plain")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        language_code = getattr(request, "LANGUAGE_CODE", "")

        if (
            not language_code.lower().startswith("en")
            or getattr(response, "streaming", False)
            or not any(
                response.get("Content-Type", "").startswith(content_type)
                for content_type in self.TRANSLATABLE_CONTENT_TYPES
            )
        ):
            return response

        from .translations import translate_to_english

        charset = response.charset or "utf-8"
        content = response.content.decode(charset)
        content = content.replace('<html lang="tr">', '<html lang="en">')
        response.content = translate_to_english(content).encode(charset)
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        return response
