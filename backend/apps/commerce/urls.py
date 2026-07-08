from django.urls import path

from . import views

urlpatterns = [
    path("cap/status/", views.status, name="cap-status"),
    path("cap/orders/", views.orders, name="cap-orders"),
    path("cap/earnings/", views.earnings, name="cap-earnings"),
    path("cap/order/", views.order, name="cap-order"),   # SELL (inbound)
    path("cap/hire/", views.hire, name="cap-hire"),       # BUY + dogfood
]
