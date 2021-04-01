from pprint import pformat

from django.conf import settings
from django.core.mail import EmailMessage
from rest_framework.reverse import reverse

from opsgrid import report_ga_event_async


def send_alert(alarm, status):
    subject = f"Opsgrid {status}: {alarm.alert.name} on {alarm.host.name}"

    body_paragraphs = [
        f'"{alarm.alert.name}" changed status on {alarm.host.name}. This was the row:'
    ]
    body_paragraphs.append(pformat(alarm.change_metric_row))
    body_paragraphs.append("Follow this link to jump to that row in your spreadsheet:")
    body_paragraphs.append(
        build_spreadsheet_link(
            alarm.host.spreadsheet_id,
            alarm.change_sheet_row_start,
            alarm.change_sheet_row_end,
        )
    )
    body_paragraphs.append(
        "To configure this alert (or delete it so you stop getting emails), follow this link:"
    )
    # TODO build this correctly for dev too
    body_paragraphs.append(
        "https://www.opsgrid.net" + reverse("alert-hretrieve", [alarm.alert.id])
    )

    email = EmailMessage(
        subject=subject,
        to=[alarm.host.user.email],
        body="\n\n".join(body_paragraphs),
        reply_to=["noreply@devnull.noreply.zone"],
    )
    email.send(fail_silently=True)

    report_ga_event_async(
        None,
        settings.GA_TRACKING_ID,
        category="alert",
        action="send",
        label=alarm.host.name,
    )


def build_spreadsheet_link(spreadsheet_id, row_start, row_end):
    # convert from indices to row count, making end inclusive
    row_start += 1

    if row_end == 1:
        # wraparound to first row
        # we don't know the last row, so just link the start
        row_end = row_start + 1
    elif row_end < row_start:
        # wraparound beyond first row
        # link from the top of the sheet
        row_start = 2

    return (
        "https://docs.google.com/spreadsheets/d"
        f"/{spreadsheet_id}/edit"
        f"#gid=0&range={row_start}:{row_end}"
    )


def build_alert_fields(header_types):
    # https://github.com/ukrbublik/react-awesome-query-builder/blob/master/CONFIG.adoc#basic-config
    alert_fields = {}
    for metric, type_name in header_types.items():
        spec = {
            "type": type_name,
            "valueSources": ["value"],
        }
        if type_name == "number":
            spec["preferWidgets"] = ["number"]

        alert_fields[metric] = spec

    return alert_fields
