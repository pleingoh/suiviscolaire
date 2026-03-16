from django.contrib import admin
from .models import School, SchoolYear, Term, GradeLevel, ClassRoom,SchoolSetting

admin.site.register(School)
admin.site.register(SchoolYear)
admin.site.register(Term)
admin.site.register(GradeLevel)
admin.site.register(ClassRoom)
admin.site.register(SchoolSetting)

