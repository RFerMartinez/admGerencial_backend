# src/utils/pdf_generator.py
import os
from io import BytesIO
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


def resolver_comprobante_pdf(venta_data: dict, items_data: list) -> bytes:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    tipo = venta_data.get("tipo_comprobante", "")
    if tipo == "Ticket":
        template = env.get_template("ticket.html")
    elif tipo == "Factura A":
        template = env.get_template("factura_a.html")
    elif tipo == "Factura B":
        template = env.get_template("factura_b.html")
    else:
        template = env.get_template("factura_b.html")

    html_out = template.render(venta=venta_data, items=items_data)

    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_out, dest=pdf_buffer)

    if pisa_status.err:
        raise Exception("Error al generar el PDF del comprobante.")

    return pdf_buffer.getvalue()
