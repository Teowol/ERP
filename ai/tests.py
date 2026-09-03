from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils.translation import override

from .views import _build_system_prompt


class _EmptyGroups:
    def filter(self, **kwargs):
        return self

    def exists(self):
        return False


class SystemPromptLanguageTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(
            groups=_EmptyGroups(),
            is_superuser=False,
            is_staff=True,
        )

    def test_system_prompt_uses_english_for_english_requests(self):
        with override("en"):
            prompt = _build_system_prompt(self.user)

        self.assertIn("Reply clearly and concisely in English", prompt)
        self.assertIn("factory owner or authorized employee", prompt)

    def test_system_prompt_keeps_turkish_for_turkish_requests(self):
        with override("tr"):
            prompt = _build_system_prompt(self.user)

        self.assertIn("Kısa, net ve Türkçe yanıt ver", prompt)
