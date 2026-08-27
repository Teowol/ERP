import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.llm import LLMService


@csrf_exempt
@require_POST
def ask(request):
    """Basit test endpoint'i: POST ile prompt alır, OpenAI'dan cevap döner."""
    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return JsonResponse({"error": "prompt alanı zorunludur"}, status=400)

        service = LLMService()
        answer = service.ask(prompt)

        return JsonResponse(
            {
                "prompt": prompt,
                "answer": answer,
                "model": service.model,
            }
        )

    except RuntimeError as e:
        return JsonResponse({"error": str(e)}, status=503)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)