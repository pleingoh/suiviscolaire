from django.shortcuts import render
from students.models import Student
from core.models import ClassRoom
from attendance.models import Attendance
from cashier.models import CashTransaction
from canteen.models import CanteenAttendance
from django.utils.timezone import now
from django.db.models import Count
from students.models import Enrollment
from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.db.models.functions import ExtractDay
from academics.models import Grade
from django.db.models import Avg


def admin_dashboard(request):

    today = now().date()

    students_count = Student.objects.count()

    classes_count = ClassRoom.objects.count()

    attendance_today = Attendance.objects.filter(date=today).count()

    canteen_today = CanteenAttendance.objects.filter(date=today).count()

    payments_today = CashTransaction.objects.filter(
        created_at__date=today,
        transaction_type="IN"
    ).count()
    classes_stats = (
        Enrollment.objects
        .values("classroom__name")
        .annotate(total=Count("id"))
    )

    payments_month = (
        CashTransaction.objects
        .annotate(month=ExtractMonth("created_at"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )

    attendance_stats = (
        Attendance.objects
        .annotate(day=ExtractDay("date"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    canteen_stats = (
        CanteenAttendance.objects
        .annotate(day=ExtractDay("date"))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )

    top_students = (
        Grade.objects
        .values("student__first_name", "student__last_name")
        .annotate(avg=Avg("score"))
        .order_by("-avg")[:10]
    )

    class_ranking = (
    Grade.objects
    .values("student__enrollments__classroom__name")
    .annotate(avg=Avg("score"))
    .order_by("-avg")
)
    
    top_students_by_class = (
    Grade.objects
    .values(
        "student__first_name",
        "student__last_name",
        "student__enrollments__classroom__name"
    )
    .annotate(avg=Avg("score"))
    .order_by(
        "student__enrollments__classroom__name",
        "-avg"
    )
)

    context = {
        "students": students_count,
        "classes": classes_count,
        "attendance_today": attendance_today,
        "canteen_today": canteen_today,
        "payments_today": payments_today,
        "context_classes": list(classes_stats),
        "context_payments": list(payments_month),
        "context_attendance": list(attendance_stats),
        "context_canteen": list(canteen_stats),
        "context_top_students": list(top_students),
        "context_class_ranking": list(class_ranking),
        "context_top_students_class": list(top_students_by_class),
    }

    return render(request, "admin/dashboard.html", context)