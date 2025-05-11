from django.shortcuts import render

# Create your views here.

def index(request):
    """
    View para servir a página de documentação da API na raiz do site.
    """
    return render(request, 'documentation/index.html')