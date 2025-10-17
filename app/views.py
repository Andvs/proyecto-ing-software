from django.shortcuts import *
from .form import *
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

# Create your views here.
def index(request):
    return render(request,"index.html")

def login(request):
    return render(request, 'login.html')

def dashboard(request):
    return render(request,"dashboard.html")

def formulario(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            contraseña_plana = form.cleaned_data['contraseña']
            usuario.contraseña = make_password(contraseña_plana)
            usuario.save()
            return redirect("formulario")
    else:
        form = UsuarioForm()
    return render(request, "formulario_usuarios.html", {"form": form})
