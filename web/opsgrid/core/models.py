import json
import uuid
from enum import Enum

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import AbstractUser
from django.db import models
from rest_framework import serializers


class EmailSocialAccount(SocialAccount):
    class Meta:
        proxy = True

    def __str__(self):
        return str(self.extra_data["email"])


class User(AbstractUser):
    pass


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        read_only_fields = "username"
        fields = read_only_fields


class IngestToken(models.Model):
    socialaccount = models.ForeignKey(EmailSocialAccount, on_delete=models.CASCADE)
    value = models.UUIDField(default=uuid.uuid4)

    def __str__(self):
        return str(self.value)


class SocialAccountPKField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        user = self.context["request"].user
        return EmailSocialAccount.objects.filter(user=user)


class IngestTokenSerializer(serializers.ModelSerializer):
    socialaccount = SocialAccountPKField()

    class Meta:
        model = IngestToken
        fields = (
            "socialaccount",
            "value",
        )
        read_only_fields = ("value",)


class HostState(Enum):
    ACTIVE = "ACT"
    # TODO handle dead hosts


class Host(models.Model):
    # upsert by ingestion
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "user"], name="unique_host_per_user"
            )
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    state = models.CharField(
        max_length=3,
        choices=[(opt.value, opt.name) for opt in HostState],
        default=HostState.ACTIVE.value,  # TODO
    )
    created_at = models.DateTimeField(auto_now_add=True)
    spreadsheet_id = models.TextField()
    last_data_at = models.DateTimeField(null=True)
    last_metric_row_json = models.TextField(blank=True)  # dict
    header_types_json = models.TextField(blank=True)  # dict

    def __str__(self):
        return str(self.name)

    @property
    def last_metric_row(self):
        return json.loads(self.last_metric_row_json)

    @property
    def header_types(self):
        return json.loads(self.header_types_json)


_host_help_text = "The host to monitor, or blank to apply to all hosts."


class Alert(models.Model):
    # created by user
    name = models.CharField(max_length=1024, help_text="A description of the alert.")
    jsonlogic_json = models.TextField()
    host = models.ForeignKey(
        Host, null=True, on_delete=models.CASCADE, help_text=_host_help_text
    )
    # user also available through host, but not if it's null
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    last_updated_at = models.DateTimeField(auto_now=True)
    alarm_hosts = models.ManyToManyField(
        Host, through="AlertAlarm", related_name="alarming_alert_set"
    )

    @property
    def jsonlogic(self):
        return json.loads(self.jsonlogic_json)

    @property
    def status(self):
        return "ALARM" if self.alarm_hosts.count() > 0 else "OK"

    def __str__(self):
        return f"{self.name} ({self.host or '<all hosts>'})"


class AlertAlarm(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["alert", "host"], name="unique_alert_by_host"
            )
        ]

    alert = models.ForeignKey(Alert, on_delete=models.CASCADE)
    host = models.ForeignKey(Host, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    change_metric_row_json = models.TextField()  # dict
    change_sheet_row_start = models.PositiveIntegerField()
    change_sheet_row_end = (
        models.PositiveIntegerField()
    )  # exclusive. can be weird on wraparounds

    @property
    def change_metric_row(self):
        return json.loads(self.change_metric_row_json)


# wtf drf
# https://stackoverflow.com/questions/57494013/in-django-rest-framework-how-to-initialize-a-field-value-for-a-createapiview-ba
class FieldQueryParamObject:
    def set_context(self, serializer_field):
        self.request = serializer_field.context["request"]
        self.value = self.request.query_params.get(self.param_key_field_name)
        self.user = self.request.user

    def __init__(self, **kwargs):
        self.param_class = kwargs["param_class"]
        self.param_key_field_name = kwargs["param_key_field_name"]

    def __call__(self, **kwargs):
        if hasattr(self, "value") and self.value:
            obj = self.param_class.objects.get(user=self.user, id=int(self.value))
            if obj:
                return obj.id
            else:
                raise serializers.ValidationError(
                    "Failed to get the object from model %s with id: %s."
                    % self.param_class.__name__,
                    self.value,
                )
        else:
            return None


class HostFromQueryPKRField(serializers.PrimaryKeyRelatedField):
    def get_initial(self):
        if callable(self.initial):
            if hasattr(self.initial, "set_context"):
                self.initial.set_context(self)
            return self.initial()
        return self.initial

    def get_queryset(self):
        return Host.objects.filter(user=self.context["request"].user)


class AlertFormSerializer(serializers.ModelSerializer):
    jsonlogic_json = serializers.CharField(
        style={"base_template": "textarea_hidden.html"}
    )
    host = HostFromQueryPKRField(
        allow_null=True,
        initial=FieldQueryParamObject(param_class=Host, param_key_field_name="host"),
        help_text=_host_help_text,
    )

    class Meta:
        model = Alert
        fields = ("id", "name", "jsonlogic_json", "host")
        read_only_fields = ("id",)


class AlertIngestSerializer(serializers.ModelSerializer):
    hostName = serializers.CharField(source="host.name", read_only=True)
    alarmHosts = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = ("id", "name", "jsonlogic", "hostName", "alarmHosts")
        read_only_fields = fields

    def get_alarmHosts(self, obj):
        return [alarm.host.name for alarm in obj.alertalarm_set.all()]
