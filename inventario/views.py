from django.shortcuts import render


def en_construccion(request, titulo):
    return render(request, "inventario/en_construccion.html", {"titulo": titulo})
