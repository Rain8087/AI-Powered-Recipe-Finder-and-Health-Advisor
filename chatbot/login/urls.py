# Author: Jordan Lau Jing Hong
# Student ID: TP064941
# Purpose: FYP

from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_user, name="login"),
    path("logout/", views.logout_user, name="logout"),
    path("register/", views.register, name="register"),
    path("mainpage/", views.mainpage, name="mainpage"),
    path("shopping-list/", views.shopping_list, name="shopping_list"),
    path("shopping-list/remove/", views.shopping_list_remove, name="shopping_list_remove"),
    path("history/", views.history, name="history"),
    path("edit-account/", views.edit_account, name="edit_account"),
    path("edit-account/update/", views.edit_account_update, name="edit_account_update"),
]
