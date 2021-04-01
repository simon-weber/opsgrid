import json
import logging

from allauth.socialaccount.models import SocialToken
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.generic import TemplateView
from rest_framework import (
    authentication,
    exceptions,
    permissions,
    serializers,
    viewsets,
)
from rest_framework.decorators import detail_route, list_route
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from opsgrid import check_google_token_expiry, report_ga_event_async
from opsgrid.core import alerts

from .models import (
    Alert,
    AlertAlarm,
    AlertFormSerializer,
    AlertIngestSerializer,
    EmailSocialAccount,
    Host,
    IngestToken,
    IngestTokenSerializer,
    User,
)

logger = logging.getLogger(__name__)


class IsOwnerOrSelf(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, User):
            return obj == request.user
        elif isinstance(obj, IngestToken):
            return obj.socialaccount.user == request.user
        else:
            return obj.user == request.user


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # todo batch/prefetch these
        user = self.request.user
        socialaccounts = EmailSocialAccount.objects.filter(user=user)
        hosts = Host.objects.filter(user=user)
        alerts = Alert.objects.filter(user=user)

        context["socialaccounts"] = socialaccounts
        context["hosts"] = hosts
        context["alerts"] = alerts

        return context


class HostSetupView(LoginRequiredMixin, TemplateView):
    template_name = "host.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        ingesttokens = IngestToken.objects.filter(socialaccount__user=user)

        context["ingesttokens"] = ingesttokens

        return context


class TokenViewSet(viewsets.ModelViewSet):
    serializer_class = IngestTokenSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrSelf)
    template_name = "token.html"

    def get_queryset(self):
        return IngestToken.objects.filter(socialaccount__user=self.request.user)

    @list_route(renderer_classes=[TemplateHTMLRenderer], template_name="tokens.html")
    def hlist(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # note that this ignores pagination
        return Response({"ingesttokens": queryset})

    @list_route(renderer_classes=[TemplateHTMLRenderer])
    def hnew(self, request, *args, **kwargs):
        serializer = self.get_serializer()
        return Response({"serializer": serializer})

    @list_route(renderer_classes=[TemplateHTMLRenderer], methods=["post"])
    def hcreate(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"serializer": serializer})
        self.perform_create(serializer)
        return redirect(reverse("token-hlist", request=request))

    @detail_route(renderer_classes=[TemplateHTMLRenderer], methods=["post"])
    def hdestroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return redirect(reverse("token-hlist", request=request))

    @detail_route(renderer_classes=[TemplateHTMLRenderer])
    def hretrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"serializer": serializer, "ingesttoken": instance})

    @detail_route(renderer_classes=[TemplateHTMLRenderer], methods=["post"])
    def hpatch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"serializer": serializer, "ingesttoken": instance})

        self.perform_update(serializer)
        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return redirect(
            reverse("token-hretrieve", args=args, kwargs=kwargs, request=request)
        )


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertFormSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwnerOrSelf)
    template_name = "alertbuilder.html"

    @staticmethod
    def _build_alert_fields(user, host=None):
        if host is None:
            header_types = {}
            for host in Host.objects.filter(user=user):
                # TODO is it possible for hosts to have different types for the same header?
                header_types.update(host.header_types)
        else:
            header_types = host.header_types

        return alerts.build_alert_fields(header_types)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user)

    @list_route(renderer_classes=[TemplateHTMLRenderer], template_name="alerts.html")
    def hlist(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        hosts = Host.objects.filter(user=self.request.user)

        # note that this ignores pagination
        return Response({"alerts": queryset, "hosts": hosts})

    @list_route(renderer_classes=[TemplateHTMLRenderer])
    def hnew(self, request, *args, **kwargs):
        serializer = self.get_serializer(context={"request": request})

        host = None
        host_id = request.query_params.get("host")
        if host_id:
            host = Host.objects.get(user=self.request.user, id=host_id)

        alert_fields = self._build_alert_fields(self.request.user, host)

        return Response({"serializer": serializer, "alert_fields": alert_fields})

    @list_route(renderer_classes=[TemplateHTMLRenderer], methods=["post"])
    def hcreate(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"serializer": serializer})
        self.perform_create(serializer)
        return redirect(reverse("alert-hlist", request=request))

    @detail_route(renderer_classes=[TemplateHTMLRenderer], methods=["post"])
    def hdestroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return redirect(reverse("alert-hlist", request=request))

    @detail_route(renderer_classes=[TemplateHTMLRenderer])
    def hretrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        alert_fields = self._build_alert_fields(self.request.user, instance.host)
        return Response(
            {"serializer": serializer, "alert": instance, "alert_fields": alert_fields}
        )

    @detail_route(renderer_classes=[TemplateHTMLRenderer], methods=["post"])
    def hpatch(self, request, *args, **kwargs):
        instance = self.get_object()
        alert_fields = self._build_alert_fields(self.request.user, instance.host)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {
                    "serializer": serializer,
                    "alert": instance,
                    "alert_fields": alert_fields,
                }
            )

        self.perform_update(serializer)
        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return redirect(reverse("alert-hlist", request=request))


class IngestTokenAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        try:
            ingest_token = IngestToken.objects.get(value=request.data["ingestToken"])
        except IngestToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("invalid ingest token")

        return (ingest_token.socialaccount.user, ingest_token)


class IngestClientPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.META.get("HTTP_X_OPSGRID_INGEST_CLIENT_SECRET")
            == settings.INGEST_CLIENT_SECRET
        )


class ExchangeToken(APIView):
    authentication_classes = [IngestTokenAuthentication]
    permission_classes = [IngestClientPermission]

    def post(self, request, format=None):
        ingest_token = self.request.auth
        socialtoken = SocialToken.objects.get(account=ingest_token.socialaccount)

        socialtoken = check_google_token_expiry(socialtoken)

        return Response(
            {"accessToken": socialtoken.token, "expiry": socialtoken.expires_at}
        )


class GetAlerts(APIView):
    authentication_classes = [IngestTokenAuthentication]
    permission_classes = [IngestClientPermission]

    def post(self, request, format=None):
        alerts = Alert.objects.prefetch_related("alertalarm_set").filter(
            user=self.request.user
        )

        return Response({"alerts": AlertIngestSerializer(alerts, many=True).data})


class ChangeAlertAlarm(APIView):
    authentication_classes = [IngestTokenAuthentication]
    permission_classes = [IngestClientPermission]

    def post(self, request, format=None):
        # TODO should probably batch these since multiple can change at once (on one host)
        status = request.data["status"]
        host_name = request.data["hostName"]
        alert_id = request.data["alertId"]
        if status == "ALARM":
            # TODO this can fail on the unique index if we get sent duplicate rows
            alarm = AlertAlarm.objects.create(
                alert_id=alert_id,
                host=Host.objects.get(name=host_name, user=request.user),
                change_metric_row_json=json.dumps(request.data["metricRow"]),
                change_sheet_row_start=request.data["sheetRowStart"],
                change_sheet_row_end=request.data["sheetRowEnd"],
            )
            logger.info(
                "added alarm for %s on alert %s",
                host_name,
                alert_id,
            )
            alerts.send_alert(alarm, status)
        elif status == "OK":
            # populate the alarm for send_alert
            alarm = AlertAlarm.objects.get(
                alert_id=alert_id, host__name=host_name, host__user=request.user
            )
            alarm.change_metric_row_json = json.dumps(request.data["metricRow"])
            alarm.change_sheet_row_start = request.data["sheetRowStart"]
            alarm.change_sheet_row_end = request.data["sheetRowEnd"]

            alerts.send_alert(alarm, status)
            logger.info(
                "removing alarm for %s on alert %s",
                host_name,
                alert_id,
            )
            # but don't actually write the fields
            alarm.delete()
        else:
            raise serializers.ValidationError(
                {"status": f"must be ALARM or OK; got {status}"}
            )

        return Response({})


class ReportMetricRow(APIView):
    authentication_classes = [IngestTokenAuthentication]
    permission_classes = [IngestClientPermission]

    def post(self, request, format=None):
        # TODO is it possible to see multiple hosts here?
        # {host: '', metricRow: [{'key': <int|str|float|bool>}]

        try:
            host = Host.objects.get(
                user=request.user,
                name=request.data["host"],
            )
        except Host.DoesNotExist:
            host = Host(
                user=request.user,
                name=request.data["host"],
                header_types_json="{}",
            )
            logger.info("new host: %s for %s", host.name, host.user)
            report_ga_event_async(
                None,
                settings.GA_TRACKING_ID,
                category="host",
                action="create",
                label=host.name,
            )

        header_types = host.header_types
        for metric, val in request.data["metricRow"].items():
            metric_type = None
            if isinstance(val, bool):
                metric_type = "boolean"
            elif isinstance(val, (float, int)):
                metric_type = "number"
            elif isinstance(val, str):
                metric_type = "text"

            if metric_type is None:
                logger.warning(
                    "unknown metric type {%s: %r} for %s %s",
                    metric,
                    val,
                    host.name,
                    host.user,
                )
            else:
                header_types[metric] = metric_type

        host.header_types_json = json.dumps(header_types)
        host.last_data_at = timezone.now()
        host.last_metric_row_json = json.dumps(request.data["metricRow"])
        host.spreadsheet_id = request.data["spreadsheetId"]

        host.save()

        report_ga_event_async(
            None,
            settings.GA_TRACKING_ID,
            category="row",
            action="report",
            label=host.name,
        )

        return Response({})


@method_decorator(cache_control(public=True, max_age=3600), name="dispatch")
class CachedView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cached_view"] = True  # base.html looks for this
        return context


class LoggedOutView(CachedView):
    template_name = "logged_out.html"


class DocsView(CachedView):
    template_name = "docs.html"


class PrivacyView(CachedView):
    template_name = "privacy.html"


class TermsView(CachedView):
    template_name = "terms.html"
