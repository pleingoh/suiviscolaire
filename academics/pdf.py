import io

from django.utils.translation import gettext as _
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def build_bulletin_pdf(payload: dict) -> bytes:
    buf = io.BytesIO()
    pdf_canvas = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    pdf_canvas.setFont("Helvetica-Bold", 16)
    pdf_canvas.drawString(2 * cm, y, _("BULLETIN SCOLAIRE"))
    y -= 1.0 * cm

    pdf_canvas.setFont("Helvetica", 11)
    pdf_canvas.drawString(2 * cm, y, f"{_('Eleve')} : {payload.get('student_name', '-')}")
    y -= 0.6 * cm
    pdf_canvas.drawString(2 * cm, y, f"{_('Classe')} : {payload.get('classroom_name', '-')}")
    y -= 0.6 * cm
    pdf_canvas.drawString(2 * cm, y, f"{_('Annee scolaire')} : {payload.get('school_year_name', '-')}")
    y -= 0.6 * cm
    pdf_canvas.drawString(2 * cm, y, f"{_('Periode')} : {payload.get('term_name', '-')}")
    y -= 1.0 * cm

    pdf_canvas.setFont("Helvetica-Bold", 11)
    pdf_canvas.drawString(2 * cm, y, _("Matiere"))
    pdf_canvas.drawRightString(width - 2 * cm, y, _("Moyenne"))
    y -= 0.4 * cm
    pdf_canvas.line(2 * cm, y, width - 2 * cm, y)
    y -= 0.6 * cm

    pdf_canvas.setFont("Helvetica", 11)
    for subject in payload.get("subjects", []):
        if y < 4 * cm:
            pdf_canvas.showPage()
            y = height - 2 * cm
            pdf_canvas.setFont("Helvetica", 11)

        pdf_canvas.drawString(2 * cm, y, str(subject.get("subject", "-")))
        pdf_canvas.drawRightString(width - 2 * cm, y, f"{float(subject.get('average', 0)):.2f}")
        y -= 0.6 * cm

    y -= 0.2 * cm
    pdf_canvas.line(2 * cm, y, width - 2 * cm, y)
    y -= 0.9 * cm

    pdf_canvas.setFont("Helvetica-Bold", 12)
    general_average = float(payload.get("general_average", 0) or 0)
    pdf_canvas.drawString(2 * cm, y, f"{_('Moyenne generale')} : {general_average:.2f}")
    y -= 0.7 * cm

    rank = payload.get("rank")
    class_size = payload.get("class_size")
    if rank is not None and class_size is not None:
        pdf_canvas.setFont("Helvetica", 11)
        pdf_canvas.drawString(2 * cm, y, f"{_('Rang')} : {rank} / {class_size}")
        y -= 0.7 * cm

    mention = payload.get("mention")
    if mention:
        pdf_canvas.drawString(2 * cm, y, f"{_('Mention')} : {mention}")
        y -= 0.7 * cm

    appreciation = payload.get("appreciation")
    if appreciation:
        pdf_canvas.drawString(2 * cm, y, f"{_('Appreciation')} : {appreciation}")
        y -= 0.7 * cm

    pdf_canvas.setFont("Helvetica", 9)
    pdf_canvas.drawString(2 * cm, 2 * cm, _("Document genere automatiquement"))
    pdf_canvas.showPage()
    pdf_canvas.save()

    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
