import datetime
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor

import google_measurement_protocol as gmp
import pytz
from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SALT = b"fj!3h9j3GHSgc$nbWS%"
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1"
)


logger = logging.getLogger(__name__)
_ga_thread_pool = ThreadPoolExecutor(4)
_token_thread_pool = ThreadPoolExecutor(2)


def check_google_token_expiry(
    socialtoken, if_expires_within=datetime.timedelta(minutes=20)
):
    now = timezone.now()
    expiry_delta = socialtoken.expires_at - now

    if socialtoken.expires_at <= now:
        logger.warning(
            "socialtoken %s expired!",
            socialtoken.id,
        )
        socialtoken = _refresh_token(socialtoken, expiry_delta)
    elif expiry_delta < if_expires_within:
        # expires soon; refresh async to prep
        _token_thread_pool.submit(_refresh_token, socialtoken, expiry_delta)

    return socialtoken


def _refresh_token(socialtoken, expiry_delta):
    c = Credentials(
        socialtoken.token,
        socialtoken.token_secret,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
        client_secret=settings.GOOGLE_OAUTH_SECRET,
    )

    logger.info(
        "refreshing socialtoken %s due to expiry in %s (at %s)",
        socialtoken.id,
        expiry_delta,
        socialtoken.expires_at,
    )
    c.refresh(Request())

    socialtoken.token = c.token
    socialtoken.expires_at = c.expiry.replace(tzinfo=pytz.UTC)
    socialtoken.token_secret = c._refresh_token  # I'm not sure if this ever changes
    socialtoken.save()

    return socialtoken


def get_client_ip(request):
    # cloudflare-specific, should be available in prod
    cf_h = request.headers.get("Cf-Connecting-Ip")
    if cf_h:
        return cf_h

    # proxy ips are appended
    forwarded_h = request.headers.get("X-Forwarded-For")
    if forwarded_h:
        return forwarded_h.split(",")[0].strip()

    # fall back to what may be a proxy's ip
    return request.headers.get("X-Real-Ip", request.headers.get("Remote-Addr"))


def report_ga_event_async(request, tracking_id, **event_kwargs):
    """
    Report a Universal Analytics event in another thread.

    event_kwargs must have category and action, and may have label and value.
    """
    from django.conf import (
        settings,
    )  # avoid import-time issues where we get prod settings

    ip = "anonymous"
    if request:
        client_ip = get_client_ip(request)
        if client_ip:
            event_kwargs["uip"] = client_ip
            ip = client_ip

    # client id must be set (even if we couldn't get an ip)
    # https://support.google.com/analytics/answer/6366371?hl=en#hashed
    h = hashlib.sha256()
    h.update(SALT)
    h.update(ip.encode())
    client_id = h.hexdigest()

    user_agent = (
        request.headers.get("User-Agent", DEFAULT_UA) if request else DEFAULT_UA
    )

    if settings.SEND_GA_EVENTS:
        _ga_thread_pool.submit(
            _report_event, client_id, user_agent, tracking_id, **event_kwargs
        )


def _report_event(client_id, user_agent, tracking_id, **event_kwargs):
    # without a proper user agent, GA may consider the traffic a bot/crawler (though it may still blacklist us by ip)
    event_kwargs["extra_headers"] = {"User-Agent": user_agent}
    try:
        logger.info("sending ga event: %r", event_kwargs)
        event = gmp.event(**event_kwargs)
        gmp.report(tracking_id, client_id, event)
    except:  # noqa
        logger.exception("failed to report event: %r", event_kwargs)
