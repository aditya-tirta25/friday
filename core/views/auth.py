from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import View


class LoginView(DjangoLoginView):
    """Handle user login."""

    template_name = "auth/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.request.GET.get("next", reverse_lazy("dashboard"))


class LogoutView(View):
    """Handle user logout."""

    def get(self, request):
        logout(request)
        messages.success(request, "You have been logged out successfully")
        return redirect("login")

    def post(self, request):
        return self.get(request)
