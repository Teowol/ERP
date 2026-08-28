import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.llm import LLMService


def json_response(data, status=200):
    return JsonResponse(
        data,
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


@csrf_exempt
@require_POST
def ask(request):
    try:
        data = json.loads(request.body)
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return json_response(
                {"error": "prompt alanı zorunludur"},
                status=400,
            )

        service = LLMService()
        answer = service.ask(prompt)

        return json_response(
            {
                "prompt": prompt,
                "answer": answer,
                "model": service.model,
            }
        )

    except RuntimeError as e:
        return json_response({"error": str(e)}, status=503)

    except Exception as e:
        return json_response({"error": str(e)}, status=500)
