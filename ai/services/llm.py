import openai
from django.conf import settings


class LLMService:
    """OpenAI API ile konuşan basit servis katmanı."""

    def __init__(self):
        self.api_key = getattr(settings, "OPENAI_API_KEY", "")
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        self.client = openai.OpenAI(api_key=self.api_key) if self.api_key else None

    def is_available(self):
        return bool(self.client and self.api_key)

    def ask(
        self,
        prompt,
        system_prompt="Sen SPEEDERS ERP için yardımcı bir asistansın.",
        temperature=0.7,
    ):
        if not self.is_available():
            raise RuntimeError("OpenAI API anahtarı yapılandırılmamış.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )

        return response.choices[0].message.content.strip()