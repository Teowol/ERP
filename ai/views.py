import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.llm import LLMService


def json_response(data, status=200):
    return JsonResponse(
        data,
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def _build_system_prompt(user):
    is_buyer = user.groups.filter(name="Buyer").exists()
    is_factory_user = (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name="FactoryOwner").exists()
    )
    use_english = get_language().lower().startswith("en")

    if use_english:
        if is_buyer:
            role_text = (
                "The user is a customer (Buyer) in the SPEEDERS system. "
                "Only assist with the product catalog, their own orders, invoices, "
                "and purchasing processes. Do not disclose factory inventory, production, "
                "quality control, or data belonging to other customers."
            )
        elif is_factory_user:
            role_text = (
                "The user is a factory owner or authorized employee in the SPEEDERS system. "
                "Assist with inventory, production, quality control, distribution, "
                "and sales operations."
            )
        else:
            role_text = (
                "The user's role could not be identified. Provide only general SPEEDERS ERP "
                "guidance and do not disclose account-specific or confidential data."
            )

        return (
            "You are a helpful AI assistant for SPEEDERS ERP. "
            "Reply clearly and concisely in English. Do not invent uncertain information. "
            f"{role_text}"
        )

    if is_buyer:
        role_text = (
            "Kullanıcı SPEEDERS sisteminde müşteridir (Buyer). "
            "Sadece ürün kataloğu, kendi siparişleri, faturaları ve satın alma "
            "süreçleri hakkında yardımcı ol. Fabrika stokları, üretim, kalite kontrol "
            "veya diğer müşterilere ait veriler hakkında bilgi verme."
        )
    elif is_factory_user:
        role_text = (
            "Kullanıcı SPEEDERS sisteminde fabrika sahibi veya yetkili personeldir. "
            "Stok, üretim, kalite kontrol, dağıtım ve satış operasyonları hakkında "
            "yardımcı ol."
        )
    else:
        role_text = (
            "Kullanıcının rolü tanımlanamadı. Sadece genel SPEEDERS ERP rehberliği yap. "
            "Hesaba özel veya gizli veri hakkında bilgi verme."
        )

    return (
        "Sen SPEEDERS ERP için yardımcı bir yapay zekâ asistanısın. "
        "Kısa, net ve Türkçe yanıt ver. Emin olmadığın bilgiyi uydurma. "
        f"{role_text}"
    )


@login_required
def chat_page(request):
    return render(request, "ai/chat.html")


@require_POST
@login_required
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
        answer = service.ask(
            prompt=prompt,
            system_prompt=_build_system_prompt(request.user),
        )

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