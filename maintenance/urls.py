from django.urls import path
from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("todo/", views.todo, name="todo"),
    path("equipment/", views.equipment_list, name="equipment"),
    path("reports/", views.reports, name="reports"),
    path("maintenance/<int:schedule_id>/complete/", views.complete_maintenance,
         name="complete_maintenance"),
]