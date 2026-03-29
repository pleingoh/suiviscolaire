from django.http import HttpResponse
from reportlab.pdfgen import canvas
from datetime import datetime

def export_dashboard_pdf(request):

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="dashboard.pdf"'

    p = canvas.Canvas(response)

    y = 800

    p.setFont("Helvetica-Bold", 18)
    p.drawString(200, y, "Rapport Suivi Scolaire")

    y -= 40

    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Date : {datetime.today().strftime('%d/%m/%Y')}")

    y -= 40

    p.drawString(50, y, "Statistiques principales")

    y -= 30

    p.drawString(70, y, f"Nombre d'élèves : {request.GET.get('students')}")
    y -= 20

    p.drawString(70, y, f"Nombre de classes : {request.GET.get('classes')}")
    y -= 20

    p.drawString(70, y, f"Présences aujourd'hui : {request.GET.get('attendance')}")
    y -= 20

    p.drawString(70, y, f"Cantine aujourd'hui : {request.GET.get('canteen')}")
    y -= 20

    p.drawString(70, y, f"Paiements aujourd'hui : {request.GET.get('payments')}")

    p.showPage()
    p.save()

    return response