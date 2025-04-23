from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserRegistrationView, PollViewSet, ChoiceViewSet

# Cria um router para ViewSets
router = DefaultRouter()
router.register(r'polls', PollViewSet) # Rota para PollViewSet
# Note: VoteViewSet e ChoiceViewSet não são registrados diretamente no router principal
# pois suas operações (criação de voto, gerenciamento de opções) são mais
# frequentemente acessadas via actions em Poll ou URLs separadas controladas por permissão.

# Não vamos registrar VoteViewSet e ChoiceViewSet diretamente no router principal
# porque as operações de voto e gerenciamento de opções são tratadas de forma específica.
# O voto é uma @action no PollViewSet.
# O gerenciamento de opções (ChoiceViewSet) está disponível em /api/choices/
# e é restrito a admins via permissões.

urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='user_register'), # Endpoint de registro
    path('', include(router.urls)), # Inclui as URLs geradas pelo router (para Polls)
    path('choices/', ChoiceViewSet.as_view({'get': 'list', 'post': 'create'}), name='choice_list_create'), # Endpoint para listar/criar opções (admin only create)
    path('choices/<int:pk>/', ChoiceViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='choice_detail_update_delete'), # Endpoint para detalhe/atualizar/excluir opção (admin only)
    # O endpoint de voto está como uma @action em PollViewSet: /api/polls/{pk}/vote/
    # O endpoint de resultados está como uma @action em PollViewSet: /api/polls/{pk}/results/
]