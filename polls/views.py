from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.contrib.auth.models import User
from django.db.models import Count # Importe para contagem de votos
from django.utils import timezone

from .models import Poll, Choice, Vote
from .serializers import (
    UserRegistrationSerializer,
    PollSerializer,
    PollCreateSerializer,
    ChoiceSerializer,
    VoteSerializer,
    PollResultSerializer
)
from .permissions import IsAdminOnly, IsAdminOrPollCreatorForChoices, CanVote
from rest_framework.exceptions import PermissionDenied

class UserRegistrationView(generics.CreateAPIView):
    """Endpoint para registro de novos usuários."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny] # Permite que qualquer um crie uma conta

class PollViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar Enquetes e Propostas."""
    queryset = Poll.objects.all().order_by('-created_at')
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated] # Default: exige autenticação

    def get_serializer_class(self):
        """Retorna o serializer apropriado para a ação."""
        if self.action == 'create':
            return PollCreateSerializer
        return PollSerializer

    def get_permissions(self):
        """Define as permissões para cada ação."""
        # Permissão para criar é IsAuthenticated (qualquer usuário logado pode criar proposta/enquete via perform_create)
        if self.action == 'create':
            self.permission_classes = [IsAuthenticated]
        # Permissão para update/delete/partial_update é IsAdminOnly (apenas admins podem editar/deletar)
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminOnly]
        # Permissão para list/retrieve/results/vote é IsAuthenticated
        elif self.action in ['list', 'retrieve', 'results', 'vote']:
            self.permission_classes = [IsAuthenticated] # Permite listar/ver detalhes/resultados/votar para qualquer autenticado
        else:
            self.permission_classes = [IsAuthenticated] # Permissão padrão

        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        """
        Sobrescreve o método create para usar PollSerializer na resposta
        mesmo que PollCreateSerializer seja usado para a entrada.
        """
        # Usa o serializer apropriado para validar e salvar os dados de entrada
        # (que será PollCreateSerializer para a action 'create')
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Executa a lógica de criação (incluindo o perform_create customizado)
        # O objeto criado estará disponível em input_serializer.instance após esta linha
        self.perform_create(input_serializer)

        # Agora, cria uma NOVA instância do PollSerializer (o completo)
        # usando o objeto Poll recém-criado como a 'instance'
        output_serializer = PollSerializer(input_serializer.instance)

        # Retorna a resposta usando os dados serializados pelo PollSerializer
        headers = self.get_success_headers(output_serializer.data) # Use output_serializer para headers
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """
        Define o criador, o tipo (enquete/proposta) na criação
        e adiciona opções padrão.
        """
        user = self.request.user
        # Salva a enquete/proposta (serializer.instance estará disponível após esta linha)
        poll_instance = serializer.save(created_by=user, is_proposal=not user.is_staff)

        # Adicionar opções padrão à enquete/proposta recém-criada
        default_choices = ["Concordo", "Discordo", "Neutro"]
        choices_to_create = [
            Choice(poll=poll_instance, choice_text=text) for text in default_choices
        ]
        Choice.objects.bulk_create(choices_to_create) # Cria as opções em massa para eficiência


    def perform_update(self, serializer):
        """Permite que admins editem enquetes/propostas."""
        # A permissão IsAdminOnly já garante que apenas admins chegam aqui
        # Admins podem editar qualquer campo, incluindo is_active e deadline
        serializer.save()

    def perform_destroy(self, instance):
        """Permite que admins excluam enquetes/propostas."""
        # A permissão IsAdminOnly já garante que apenas admins chegam aqui
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[CanVote])
    def vote(self, request, pk=None):
        """Endpoint para votar em uma enquete/proposta."""
        poll = self.get_object() # Obtém a enquete pelo PK

        # Usa o VoteSerializer para validar e criar o voto
        # Passamos a enquete encontrada para o serializer
        serializer = VoteSerializer(data=request.data, context={'request': request, 'poll': poll})

        if serializer.is_valid():
            # O serializer já tem a lógica de validação (enquete ativa, não votou, etc.)
            serializer.save()
            return Response({'status': 'voted', 'vote': serializer.data}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def results(self, request, pk=None):
        """Endpoint para visualizar os resultados de uma enquete/proposta, incluindo total e porcentagem."""
        poll = self.get_object() # Obtém a enquete pelo PK

        # Calcula o total de votos para esta enquete
        total_poll_votes = Vote.objects.filter(poll=poll).count()

        # Consulta as opções desta enquete, anota com a contagem de votos para cada opção,
        # e seleciona apenas o texto da opção e a contagem.
        results_data = Choice.objects.filter(poll=poll).annotate(vote_count=Count('votes')).values('choice_text', 'vote_count')

        # Serializa os dados, passando o total de votos no contexto
        # O serializer usará este contexto para calcular a porcentagem.
        serializer = PollResultSerializer(results_data, many=True, context={'total_votes': total_poll_votes})

        # Opcional: Adicionar o total de votos da enquete no nível superior da resposta
        # Crie um dicionário combinando o total e os resultados detalhados.
        response_data = {
            'poll_id': poll.id,
            'poll_title': poll.title,
            'total_votes': total_poll_votes,
            'choices_results': serializer.data,
            'is_active': poll.is_active, # Pode ser útil saber se ainda está ativa
            'deadline': poll.deadline,
        }


        return Response(response_data)

class ChoiceViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciar Opções de Voto."""
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    # Permissão padrão: apenas admins. Sobrescrevemos para ações específicas.
    permission_classes = [IsAdminOnly]

    def get_permissions(self):
        """Define permissões customizadas por ação no ChoiceViewSet."""
        if self.action == 'create':
            # Permitir que QUALQUER usuário autenticado TENTE criar uma opção.
            # A verificação detalhada (se é admin OU dono da proposta)
            # acontecerá DENTRO do método perform_create, onde temos acesso ao objeto Poll associado.
            self.permission_classes = [IsAuthenticated]
        elif self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
             # Listar, ver detalhes, atualizar ou excluir opções é APENAS para admins
             self.permission_classes = [IsAdminOnly]
        else:
            # Permissão padrão para outras ações não explicitadas (se houver)
            self.permission_classes = [IsAdminOnly]

        return [permission() for permission in self.permission_classes]


    def perform_create(self, serializer):
        """
        Sobrescreve perform_create para adicionar a lógica de permissão:
        admins podem criar opções para qualquer enquete/proposta.
        Usuários comuns podem criar opções APENAS para SUAS propostas.
        """
        user = self.request.user
        # Obtém o objeto Poll associado à opção que está sendo criada
        # (o serializer já validou que o poll existe e é um campo válido)
        poll = serializer.validated_data['poll']

        # Lógica de Permissão Detalhada para Criação de Opção:
        # Se o usuário NÃO FOR administrador:
        #   Ele SÓ TEM permissão para criar a opção SE
        #   ( a enquete/proposta for marcada como proposta (is_proposal=True) E
        #     o usuário autenticado for o MESMO que criou essa proposta (created_by) )
        # Caso contrário (se não for admin E não for o dono da proposta OU não for uma proposta), nega a permissão.
        if not user.is_staff: # Verifica se NÃO é um administrador
            if not (poll.is_proposal and poll.created_by == user):
                # Se NÃO for a proposta que ele criou OU se a enquete/proposta não for uma proposta (i.e., for enquete de admin),
                # lança uma exceção de permissão negada.
                raise PermissionDenied("Você só pode adicionar opções a propostas que você criou.")

            # Opcional: Adicionar validação extra para não adicionar opções a propostas já ativas/com votos?
            # Para um sistema de votação "real", pode ser importante não permitir adicionar opções
            # depois que a votação começou. Se precisar, adicione esta verificação:
            # if not poll.is_active: # Assumindo que propostas inativas podem ser editadas
            #      raise PermissionDenied("Não é possível adicionar opções a propostas que não estão ativas.")
            # Ou:
            # if Vote.objects.filter(poll=poll).exists():
            #      raise PermissionDenied("Não é possível adicionar opções a enquetes ou propostas que já receberam votos.")


        # Se a execução chegou até aqui, significa que o usuário tem permissão para criar a opção:
        # - Ou porque é um administrador (passou pela primeira checagem 'if not user.is_staff').
        # - Ou porque não é administrador, mas passou pela checagem aninhada (é o dono da proposta).
        # Agora podemos salvar a opção.
        serializer.save()

    # Note: perform_update e perform_destroy não precisam ser sobrescritos aqui para permissão,
    # pois get_permissions já as restringe a IsAdminOnly, o que está correto com a regra
    # de que apenas admins editam/excluem opções (mesmo nas propostas dos usuários comuns).