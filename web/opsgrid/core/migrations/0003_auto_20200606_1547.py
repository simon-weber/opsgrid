# Generated by Django 2.2.9 on 2020-06-06 15:47

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import opsgrid.core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_auto_20200530_2351"),
    ]

    operations = [
        migrations.CreateModel(
            name="Alert",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("jsonlogic_json", models.TextField()),
                ("last_updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Host",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=256)),
                (
                    "state",
                    models.CharField(
                        choices=[(opsgrid.core.models.HostState("ACT"), "ACT")],
                        default="ACT",
                        max_length=3,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_data_at", models.DateTimeField(null=True)),
                ("last_metric_row_json", models.TextField(blank=True)),
                ("header_types_json", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AlertStatus",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("ALARM", "ALM"),
                            ("OK", "OK"),
                        ],
                        default="OK",
                        max_length=3,
                    ),
                ),
                (
                    "last_change_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("change_metric_row_json", models.TextField(blank=True)),
                (
                    "alert",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="core.Alert"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="alert",
            name="host",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="core.Host"
            ),
        ),
        migrations.AddConstraint(
            model_name="host",
            constraint=models.UniqueConstraint(
                fields=("name", "user"), name="unique_host_per_user"
            ),
        ),
    ]
