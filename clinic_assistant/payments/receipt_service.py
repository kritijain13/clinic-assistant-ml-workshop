from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


BASE_DIR = Path(__file__).resolve().parents[1]
RECEIPT_DIR = BASE_DIR / "receipts"

RECEIPT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def generate_receipt(details):

    payment = details["payment"]
    appointment = details["appointment"]
    patient = details["patient"]
    doctor = details["doctor"]
    slot = details["slot"]

    receipt_number = f"REC-{payment.id:06d}"

    receipt_path = (
        RECEIPT_DIR /
        f"payment_receipt_{payment.id}.pdf"
    )

    pdf = canvas.Canvas(
        str(receipt_path),
        pagesize=A4
    )

    width, height = A4

    # Title
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(
        width / 2,
        height - 70,
        "SANJEEVANI CLINIC"
    )

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(
        width / 2,
        height - 90,
        "Appointment Payment Receipt"
    )

    # Line
    pdf.line(
        50,
        height - 110,
        width - 50,
        height - 110
    )

    y = height - 145

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(60, y, "Receipt Number:")
    
    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        180,
        y,
        receipt_number
    )

    y -= 25

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(60, y, "Transaction ID:")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        180,
        y,
        payment.transaction_id or "-"
    )

    y -= 35

    # Patient details
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(
        60,
        y,
        "Patient Details"
    )

    y -= 25

    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        60,
        y,
        f"Name: {patient.name}"
    )

    y -= 20

    pdf.drawString(
        60,
        y,
        f"Email: {patient.email}"
    )

    y -= 35

    # Doctor details
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(
        60,
        y,
        "Appointment Details"
    )

    y -= 25

    pdf.setFont("Helvetica", 11)

    pdf.drawString(
        60,
        y,
        f"Doctor: {doctor.name}"
    )

    y -= 20

    pdf.drawString(
        60,
        y,
        f"Specialization: {doctor.specialization}"
    )

    y -= 20

    pdf.drawString(
        60,
        y,
        f"Date: {slot.slot_date}"
    )

    y -= 20

    pdf.drawString(
        60,
        y,
        f"Time: {slot.slot_time}"
    )

    y -= 20

    pdf.drawString(
        60,
        y,
        f"Reason: {appointment.reason or '-'}"
    )

    y -= 35

    # Payment details
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(
        60,
        y,
        "Payment Details"
    )

    y -= 25

    pdf.setFont("Helvetica", 11)

    pdf.drawString(
        60,
        y,
        f"Amount Paid: Rs. {payment.amount:.2f}"
    )

    y -= 20

    pdf.drawString(
        60,
        y,
        f"Payment Status: {payment.payment_status.upper()}"
    )

    y -= 20

    payment_date = (
        payment.payment_date.strftime("%d-%m-%Y %I:%M %p")
        if payment.payment_date
        else "-"
    )

    pdf.drawString(
        60,
        y,
        f"Payment Date: {payment_date}"
    )

    y -= 50

    pdf.setFont("Helvetica-Bold", 11)

    pdf.drawString(
        60,
        y,
        "Thank you for choosing Sanjeevani Clinic."
    )

    y -= 20

    pdf.setFont("Helvetica", 9)

    pdf.drawString(
        60,
        y,
        "This is a computer-generated payment receipt."
    )

    pdf.save()

    return str(receipt_path)