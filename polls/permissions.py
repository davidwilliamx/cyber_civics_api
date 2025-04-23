from rest_framework import permissions

class IsAdminOnly(permissions.BasePermission):
    """Permissão para permitir acesso apenas a usuários administradores."""
    def has_permission(self, request, view):
        # Somente permite se o usuário for autenticado e for staff (admin)
        return request.user and request.user.is_authenticated and request.user.is_staff

class IsAdminOrOwner(permissions.BasePermission):
    """Permissão para permitir acesso a administradores ou ao criador do objeto."""
    def has_object_permission(self, request, view, obj):
        # Permite acesso de leitura para qualquer solicitação autenticada (se for o caso, mas aqui focamos na escrita/edição)
        # if request.method in permissions.SAFE_METHODS:
        #     return True

        # Permite se for um administrador
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True

        # Permite se o usuário for o criador do objeto (assume que o objeto tem um campo 'created_by' ou similar)
        # Note: Esta permissão é mais genérica. Em Poll, apenas admins editam/deletam.
        # Em outros contextos onde usuários podem editar seus próprios objetos, esta seria útil.
        # Para este projeto, Poll e Choice edição/delete são apenas para admin. Vote é apenas create.
        # Vamos manter IsAdminOnly para Poll/Choice edição/delete.

        # Retorna False por padrão se nenhuma das condições for atendida
        return False

class IsAdminOrPollCreatorForChoices(permissions.BasePermission):
    """Permissão para gerenciar opções: apenas admin ou o criador da proposta (se for proposta)."""
    def has_permission(self, request, view):
        # Permite listar opções para todos autenticados
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        # Para criação, verificar o objeto Poll associado na view
        return request.user and request.user.is_authenticated # A validação real ocorre na view/serializer

    def has_object_permission(self, request, view, obj):
        # Permite acesso de leitura para qualquer solicitação autenticada
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Permite se for um administrador
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True

        # Se for uma proposta (is_proposal=True), permite ao criador da proposta
        if obj.poll.is_proposal and obj.poll.created_by == request.user:
             return True

        # Senão, nega o acesso
        return False

class CanVote(permissions.BasePermission):
    """Permissão para votar: Apenas usuários autenticados e na enquete/proposta correta (verificação na view/serializer)."""
    def has_permission(self, request, view):
        # Apenas permite se o usuário estiver autenticado.
        # A lógica se a enquete está ativa ou se já votou é feita no serializer/view.
        return request.user and request.user.is_authenticated