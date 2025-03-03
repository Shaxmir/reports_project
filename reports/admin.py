from django.contrib import admin
from reports.models import Sale, Expense, CashRegister

# Register your models here.
admin.site.register(Sale)
admin.site.register(Expense)
admin.site.register(CashRegister)