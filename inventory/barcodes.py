import base64
from io import BytesIO

import barcode
import qrcode
from barcode.writer import SVGWriter
from django.utils.html import format_html
from qrcode.image.svg import SvgPathImage


def _data_uri(data):
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii")


def barcode_svg_data_uri(value):
    output = BytesIO()
    barcode.get("code128", value, writer=SVGWriter()).write(
        output, options={"write_text": True, "module_height": 10, "quiet_zone": 2}
    )
    return _data_uri(output.getvalue())


def qr_svg_data_uri(payload):
    image = qrcode.make(payload, image_factory=SvgPathImage)
    output = BytesIO()
    image.save(output)
    return _data_uri(output.getvalue())


def admin_code_preview(obj):
    if not obj or not obj.barcode or not obj.qr_code:
        return "-"
    return format_html(
        "<div style=\"display:flex;gap:16px;align-items:center\">"
        "<img src=\"{}\" alt=\"Barkod\" style=\"max-width:360px;height:90px\">"
        "<img src=\"{}\" alt=\"QR kod\" style=\"width:120px;height:120px\"></div>",
        barcode_svg_data_uri(obj.barcode), qr_svg_data_uri(obj.qr_code),
    )
