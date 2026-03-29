from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Avg
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
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SchoolForm
from .models import School


@staff_member_required
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
        "schools_count": School.objects.count(),
        "context_classes": list(classes_stats),
        "context_payments": list(payments_month),
        "context_attendance": list(attendance_stats),
        "context_canteen": list(canteen_stats),
        "context_top_students": list(top_students),
        "context_class_ranking": list(class_ranking),
        "context_top_students_class": list(top_students_by_class),
    }

    return render(request, "admin/dashboard.html", context)


@staff_member_required
def admin_school_list(request):
    schools = School.objects.order_by("name")
    return render(request, "admin/schools.html", {"schools": schools})


@staff_member_required
def admin_school_edit(request, pk):
    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        form = SchoolForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "L'ecole a ete mise a jour.")
            return redirect("admin-school-list")
    else:
        form = SchoolForm(instance=school)

    return render(
        request,
        "admin/school_form.html",
        {"form": form, "school": school},
    )


@staff_member_required
def admin_school_delete(request, pk):
    school = get_object_or_404(School, pk=pk)

    if request.method == "POST":
        school_name = school.name
        with transaction.atomic():
            school.delete()
        messages.success(request, f"L'ecole {school_name} a ete supprimee.")
        return redirect("admin-school-list")

    related_counts = {
        "annees_scolaires": school.years.count(),
        "niveaux": school.grade_levels.count(),
    }
    return render(
        request,
        "admin/school_confirm_delete.html",
        {"school": school, "related_counts": related_counts},
    )
