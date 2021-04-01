import logging

from allauth.socialaccount.signals import social_account_added
from django.dispatch.dispatcher import receiver

from opsgrid.core.models import IngestToken

logger = logging.getLogger(__name__)


@receiver(social_account_added)
def create_ingest_token(sender, request, sociallogin, **kwargs):
    t = IngestToken.objects.create(socialaccount=sociallogin.account)
    logger.info("created ingesttoken %r for login to %r", t, sociallogin.account)


# @receiver(social_account_removed)
# def remove_ingest_token(sender, request, socialaccount, **kwargs):
#     # I think this should cascade
#     pass
