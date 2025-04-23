from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
from .models import Poll, Choice, Vote

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuário."""
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''), # Email opcional
            password=validated_data['password']
        )
        return user

class ChoiceSerializer(serializers.ModelSerializer):
    """Serializer para opções de voto."""
    class Meta:
        model = Choice
        fields = ('id', 'choice_text', 'poll') # Inclui 'poll' para criação/atualização, mas pode ser 'read_only=True' em outros contextos

class PollSerializer(serializers.ModelSerializer):
    """Serializer para Enquetes/Propostas."""
    choices = ChoiceSerializer(many=True, read_only=True) # Exibe as opções, mas não permite criar via este serializer
    created_by = serializers.ReadOnlyField(source='created_by.username') # Exibe o nome do criador (somente leitura)
    is_active = serializers.BooleanField(read_only=True) # is_active é controlado pelo admin, não pelo serializer padrão
    is_proposal = serializers.BooleanField(read_only=True) # is_proposal é definido na view na criação

    class Meta:
        model = Poll
        fields = ('id', 'title', 'description', 'created_by', 'created_at', 'deadline', 'is_active', 'is_proposal', 'choices')
        read_only_fields = ('created_at',) # created_at é gerado automaticamente

class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de Enquetes/Propostas (para diferenciar a lógica de permissão/is_proposal)."""
    # Note que choices não está aqui, pois serão criadas separadamente ou por outra view/action
    class Meta:
        model = Poll
        fields = ('title', 'description', 'deadline') # Campos que podem ser definidos na criação

class VoteSerializer(serializers.ModelSerializer):
    """Serializer para registrar um voto."""
    user = serializers.ReadOnlyField(source='user.username') # Exibe o nome do usuário (somente leitura)

    class Meta:
        model = Vote
        # Remova 'poll' dos fields, pois ele será obtido do contexto da view,
        # não dos dados de entrada do request.
        fields = ('id', 'choice', 'user', 'voted_at')
        read_only_fields = ('voted_at',)

    def create(self, validated_data):
        user = self.context['request'].user
        # Obtenha o objeto poll do contexto que a view passou
        poll = self.context.get('poll') # Use .get() para segurança, embora a view o forneça

        # Verificação caso o poll não esteja no contexto (não deve acontecer com a view correta)
        if not poll:
             raise serializers.ValidationError("Erro interno: Enquete não fornecida no contexto.")

        choice = validated_data['choice']

        # Validar se a opção pertence à enquete fornecida no contexto
        if choice.poll != poll:
            raise serializers.ValidationError({"choice": ["Esta opção não pertence a esta enquete."]}) # Use lista para consistência com outros erros

        # Validar se a enquete está ativa (agora usa o objeto poll do contexto)
        if not poll.is_active or (poll.deadline and poll.deadline < timezone.now()):
             raise serializers.ValidationError({"non_field_errors": ["Não é possível votar em uma enquete inativa ou expirada."]}) # Use non_field_errors para erros gerais

        # Validar se o usuário já votou nesta enquete (agora usa o objeto poll do contexto)
        if Vote.objects.filter(user=user, poll=poll).exists():
            raise serializers.ValidationError({"non_field_errors": ["Você já votou nesta enquete."]}) # Use non_field_errors


        # Tentar criar o voto
        try:
            # Crie o voto usando o objeto poll obtido do contexto
            vote = Vote.objects.create(user=user, poll=poll, choice=choice)
            return vote
        except IntegrityError:
             # Esta exceção é menos provável agora com as validações acima, mas é uma garantia extra.
             raise serializers.ValidationError({"non_field_errors": ["Erro ao registrar o voto. Possível problema de duplicidade."]})



class PollResultSerializer(serializers.Serializer):
    """Serializer para exibir os resultados de uma enquete, incluindo porcentagem."""
    choice_text = serializers.CharField()
    vote_count = serializers.IntegerField()
    percentage = serializers.SerializerMethodField() # Campo para a porcentagem

    def get_percentage(self, obj):
        """Calcula a porcentagem de votos para esta opção."""
        # obj aqui é um dicionário {'choice_text': ..., 'vote_count': ...}
        vote_count = obj['vote_count']
        # O total de votos da enquete é passado no contexto do serializer
        total_votes = self.context.get('total_votes', 0)

        if total_votes == 0:
            return 0.0 # Evita divisão por zero
        # Calcula a porcentagem e arredonda para 2 casas decimais
        return round((vote_count / total_votes) * 100, 2)