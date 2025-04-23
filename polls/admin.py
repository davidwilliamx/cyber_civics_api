from django.contrib import admin
from .models import Poll, Choice, Vote

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'deadline', 'is_active', 'is_proposal')
    list_filter = ('is_active', 'is_proposal', 'created_at', 'deadline')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',) # created_at não deve ser editável manualmente
    # Permite que admins editem tudo via admin, incluindo is_active e deadline
    fields = ('title', 'description', 'created_by', 'deadline', 'is_active', 'is_proposal', 'created_at')

    def get_queryset(self, request):
        # No admin, superusuários veem tudo. Staff normal só veria seus criados,
        # mas para simplicidade aqui, todos admins veem tudo.
        qs = super().get_queryset(request)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # No admin, o campo created_by para Polls criados por admins pode ser selecionado (embora setado automaticamente na API)
        if db_field.name == "created_by" and not request.user.is_superuser:
             # Se não for superuser, apenas mostra ele mesmo como opção
             kwargs["queryset"] = request.user.__class__.objects.filter(pk=request.user.pk)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('choice_text', 'poll')
    list_filter = ('poll',)
    search_fields = ('choice_text',)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'poll', 'choice', 'voted_at')
    list_filter = ('user', 'poll', 'voted_at')
    search_fields = ('user__username', 'poll__title', 'choice__choice_text')
    readonly_fields = ('voted_at',) # voted_at não deve ser editável manualmente