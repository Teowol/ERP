from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Color, ProductVariant, ShoeModel, Size


def product_list(request):
    variants = ProductVariant.objects.select_related(
        "shoe_model",
        "color",
        "size",
        "product",
        "product__category",
    )

    query = request.GET.get("q", "").strip()
    model_id = request.GET.get("model", "").strip()
    color_id = request.GET.get("color", "").strip()
    size_id = request.GET.get("size", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        variants = variants.filter(
            Q(sku__icontains=query)
            | Q(shoe_model__code__icontains=query)
            | Q(shoe_model__name__icontains=query)
            | Q(product__code__icontains=query)
            | Q(product__name__icontains=query)
        )

    if model_id:
        variants = variants.filter(shoe_model_id=model_id)

    if color_id:
        variants = variants.filter(color_id=color_id)

    if size_id:
        variants = variants.filter(size_id=size_id)

    if status == "active":
        variants = variants.filter(is_active=True)
    elif status == "passive":
        variants = variants.filter(is_active=False)

    context = {
        "variants": variants,
        "shoe_models": ShoeModel.objects.filter(is_active=True),
        "colors": Color.objects.all(),
        "sizes": Size.objects.all(),
        "query": query,
        "selected_model": model_id,
        "selected_color": color_id,
        "selected_size": size_id,
        "selected_status": status,
    }

    return render(request, "catalog/product_list.html", context)


def product_detail(request, pk):
    variant = get_object_or_404(
        ProductVariant.objects.select_related(
            "shoe_model",
            "color",
            "size",
            "product",
            "product__category",
        ),
        pk=pk,
    )

    stocks = variant.product.stocks.select_related("warehouse")

    return render(
        request,
        "catalog/product_detail.html",
        {
            "variant": variant,
            "stocks": stocks,
        },
    )
