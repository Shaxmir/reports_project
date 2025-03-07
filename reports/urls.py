from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, ExpenseViewSet, CashRegisterViewSet, daily_report, add_expense, update_cash, update_expense

router = DefaultRouter()
router.register(r'sales', SaleViewSet)
router.register(r'expenses', ExpenseViewSet)
router.register(r'cash_register', CashRegisterViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/report/', daily_report, name="daily_report"),
    path('api/expenses/', add_expense, name="add_expense"),
    path("api/expenses/<int:expense_id>/", update_expense, name="update_expense"),
    path('api/cash/', update_cash, name="update_cash"),

]
