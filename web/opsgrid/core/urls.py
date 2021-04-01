from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"tokens", views.TokenViewSet, "token")
router.register(r"alerts", views.AlertViewSet, "alert")

urlpatterns = [
    path("", views.LoggedOutView.as_view()),
    path("docs", views.DocsView.as_view(), name="docs"),
    path("privacy", views.PrivacyView.as_view(), name="privacy"),
    path("terms", views.TermsView.as_view(), name="terms"),
    path("dashboard", views.DashboardView.as_view(), name="dashboard"),
    path("host", views.HostSetupView.as_view(), name="host-setup"),
    path("api/", include(router.urls)),
    path(
        "ingest/exchange", views.ExchangeToken.as_view(), name="ingest-exchange-token"
    ),
    path("ingest/row", views.ReportMetricRow.as_view(), name="ingest-report-row"),
    path("ingest/alerts", views.GetAlerts.as_view(), name="ingest-get-alerts"),
    path(
        "ingest/alarm",
        views.ChangeAlertAlarm.as_view(),
        name="ingest-change-alert-alarm",
    ),
]
