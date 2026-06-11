# src/utils/pdf_generator.py
import os
from io import BytesIO
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

def resolver_comprobante_pdf(venta_data: dict, items_data: list) -> bytes:
    """
    Toma los datos de la venta y devuelve el PDF en formato de bytes,
    utilizando xhtml2pdf que es 100% compatible con Windows sin librerías extra.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    
    # Enrutamiento de plantillas basado en el tipo de comprobante
    if venta_data.get("tipo_comprobante") == "Ticket":
        template = env.get_template("ticket.html")
    else:
        template = env.get_template("factura.html")
        
    # Renderizamos el HTML con las variables
    html_out = template.render(venta=venta_data, items=items_data)
    
    # Creamos un buffer de memoria para guardar el archivo temporalmente
    pdf_buffer = BytesIO()
    
    # Convertimos el HTML a PDF
    pisa_status = pisa.CreatePDF(html_out, dest=pdf_buffer)
    
    if pisa_status.err:
        raise Exception("Error al generar el PDF del comprobante.")
        
    return pdf_buffer.getvalue()