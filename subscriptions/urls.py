from django.urls import path
from .views import create_checkout_session, stripe_webhook, member_area

urlpatterns = [
    path("checkout/", create_checkout_session),
    path("webhook/", stripe_webhook),
    path("member-area/", member_area),
]
