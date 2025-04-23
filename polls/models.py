from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

class Poll(models.Model):
    """Representa uma enquete ou proposta."""
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_polls')
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True) # Data limite para votar
    is_active = models.BooleanField(default=True) # Indica se a enquete está aberta para votação
    is_proposal = models.BooleanField(default=False) # True se for uma proposta de usuário, False se for uma enquete de admin

    def __str__(self):
        return self.title

    def clean(self):
        # Validação simples: a data limite não pode ser no passado (a menos que já esteja inativa)
        if self.deadline and self.deadline < timezone.now() and self.is_active:
             raise ValidationError('A data limite não pode ser no passado para uma enquete ativa.')


class Choice(models.Model):
    """Representa uma opção de voto em uma enquete."""
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.poll.title}: {self.choice_text}"

    class Meta:
        unique_together = ('poll', 'choice_text') # Garante que não há opções duplicadas na mesma enquete


class Vote(models.Model):
    """Registra o voto de um usuário em uma opção de uma enquete."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes_for_poll') # Relação para facilitar consultas
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='votes')
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'poll') # Garante que um usuário vota apenas uma vez por enquete

    def clean(self):
        # Validação para garantir que o voto é para uma opção da enquete correta
        if self.choice.poll != self.poll:
             raise ValidationError('A opção de voto não pertence a esta enquete.')

    def __str__(self):
        return f"{self.user.username} votou em '{self.choice.choice_text}' na enquete '{self.poll.title}'"