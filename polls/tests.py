from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from .models import Poll, Choice, Vote

class PollsAPITestCase(APITestCase):
    """Classe de testes para a API de Enquetes."""

    def setUp(self):
        """Configura o ambiente de teste."""
        # Criar usuário administrador
        self.admin_user = User.objects.create_superuser(username='admin', password='adminpassword')
        self.admin_client = APIClient()
        response = self.admin_client.post(reverse('api_token_auth'), {'username': 'admin', 'password': 'adminpassword'})
        self.admin_token = response.data['token']
        self.admin_client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token)

        # Criar usuário comum
        self.regular_user = User.objects.create_user(username='regular', password='regularpassword')
        self.regular_client = APIClient()
        response = self.regular_client.post(reverse('api_token_auth'), {'username': 'regular', 'password': 'regularpassword'})
        self.regular_token = response.data['token']
        self.regular_client.credentials(HTTP_AUTHORIZATION='Token ' + self.regular_token)

        # Cliente sem autenticação
        self.unauthenticated_client = APIClient()

        # URLs da API (usando reverse para maior robustez)
        self.poll_list_create_url = reverse('poll-list') # Nome da URL gerada pelo router
        self.choice_list_create_url = reverse('choice_list_create') # Nome da URL definida explicitamente
        self.register_url = reverse('user_register') # Nome da URL definida explicitamente

        # Criar uma enquete e uma proposta para testes
        self.admin_poll = Poll.objects.create(
            title="Admin Poll",
            description="Poll created by admin",
            created_by=self.admin_user,
            deadline=timezone.now() + timedelta(days=7),
            is_active=True,
            is_proposal=False # Admins criam enquetes
        )
        self.regular_proposal = Poll.objects.create(
            title="Regular Proposal",
            description="Proposal created by regular user",
            created_by=self.regular_user,
            is_active=True, # Propostas podem ser ativas ou não, dependendo da lógica de aprovação (fora do escopo atual)
            is_proposal=True # Usuários comuns criam propostas
        )

        # Criar opções para a enquete do admin
        self.admin_choice1 = Choice.objects.create(poll=self.admin_poll, choice_text="Option A")
        self.admin_choice2 = Choice.objects.create(poll=self.admin_poll, choice_text="Option B")

        # Criar opções para a proposta do usuário comum (nossa regra atual é que APENAS admins podem criar Choices diretamente)
        # Para testar a votação em proposta, um admin precisaria criar as opções para ela.
        self.proposal_choice1 = Choice.objects.create(poll=self.regular_proposal, choice_text="Prop Option 1")


    # --- Testes de Autenticação e Registro ---

    def test_user_registration(self):
        """Testa o registro de um novo usuário."""
        data = {'username': 'newuser', 'password': 'newpassword', 'email': 'newuser@example.com'}
        response = self.unauthenticated_client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login(self):
        """Testa o login de um usuário e a obtenção do token."""
        data = {'username': 'regular', 'password': 'regularpassword'}
        response = self.unauthenticated_client.post(reverse('api_token_auth'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)


    # --- Testes de Gerenciamento de Polls (Enquetes/Propostas) ---

    # Testes de Criação
    def test_admin_can_create_poll(self):
        """Admin pode criar uma enquete (is_proposal=False)."""
        data = {'title': 'New Admin Poll', 'description': 'Admin can create this.', 'deadline': '2026-01-01T10:00:00Z'}
        response = self.admin_client.post(self.poll_list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Poll.objects.filter(title='New Admin Poll').exists())
        # Verificar se is_proposal é False para admin
        new_poll = Poll.objects.get(title='New Admin Poll')
        self.assertFalse(new_poll.is_proposal)
        self.assertEqual(new_poll.created_by, self.admin_user)


    def test_regular_user_can_create_proposal(self):
        """Usuário comum pode criar uma proposta (is_proposal=True)."""
        data = {'title': 'New Regular Proposal', 'description': 'Regular user creates this.'}
        response = self.regular_client.post(self.poll_list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Poll.objects.filter(title='New Regular Proposal').exists())
        # Verificar se is_proposal é True para usuário comum
        new_proposal = Poll.objects.get(title='New Regular Proposal')
        self.assertTrue(new_proposal.is_proposal)
        self.assertEqual(new_proposal.created_by, self.regular_user)


    def test_unauthenticated_user_cannot_create_poll(self):
        """Usuário não autenticado NÃO pode criar enquete/proposta."""
        data = {'title': 'Should Fail', 'description': 'This should not be created.'}
        response = self.unauthenticated_client.post(self.poll_list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Poll.objects.filter(title='Should Fail').exists())


    # Testes de Listagem e Detalhe
    def test_authenticated_user_can_list_polls(self):
        """Usuário autenticado (admin ou comum) pode listar enquetes/propostas."""
        response_admin = self.admin_client.get(self.poll_list_create_url, format='json')
        self.assertEqual(response_admin.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response_admin.data), 2) # Deve listar pelo menos a enquete e a proposta criadas no setup

        response_regular = self.regular_client.get(self.poll_list_create_url, format='json')
        self.assertEqual(response_regular.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response_regular.data), 2)


    def test_unauthenticated_user_cannot_list_polls(self):
        """Usuário não autenticado NÃO pode listar enquetes/propostas."""
        response = self.unauthenticated_client.get(self.poll_list_create_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_authenticated_user_can_retrieve_poll(self):
        """Usuário autenticado (admin ou comum) pode ver detalhes de uma enquete/proposta."""
        url = reverse('poll-detail', args=[self.admin_poll.id])
        response_admin = self.admin_client.get(url, format='json')
        self.assertEqual(response_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(response_admin.data['title'], self.admin_poll.title)

        url = reverse('poll-detail', args=[self.regular_proposal.id])
        response_regular = self.regular_client.get(url, format='json')
        self.assertEqual(response_regular.status_code, status.HTTP_200_OK)
        self.assertEqual(response_regular.data['title'], self.regular_proposal.title)


    def test_unauthenticated_user_cannot_retrieve_poll(self):
        """Usuário não autenticado NÃO pode ver detalhes de enquete/proposta."""
        url = reverse('poll-detail', args=[self.admin_poll.id])
        response = self.unauthenticated_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    # Testes de Atualização
    def test_admin_can_update_any_poll(self):
        """Admin pode atualizar qualquer enquete/proposta."""
        url_admin_poll = reverse('poll-detail', args=[self.admin_poll.id])
        data_admin_poll = {'title': 'Updated Admin Poll'}
        response_admin_poll = self.admin_client.patch(url_admin_poll, data_admin_poll, format='json')
        self.assertEqual(response_admin_poll.status_code, status.HTTP_200_OK)
        self.admin_poll.refresh_from_db()
        self.assertEqual(self.admin_poll.title, 'Updated Admin Poll')

        url_regular_proposal = reverse('poll-detail', args=[self.regular_proposal.id])
        data_regular_proposal = {'description': 'Updated Proposal Description'}
        response_regular_proposal = self.admin_client.patch(url_regular_proposal, data_regular_proposal, format='json')
        self.assertEqual(response_regular_proposal.status_code, status.HTTP_200_OK)
        self.regular_proposal.refresh_from_db()
        self.assertEqual(self.regular_proposal.description, 'Updated Proposal Description')


    def test_regular_user_cannot_update_poll(self):
        """Usuário comum NÃO pode atualizar enquete/proposta (nem mesmo a sua)."""
        url_admin_poll = reverse('poll-detail', args=[self.admin_poll.id])
        data = {'title': 'Attempted Update'}
        response = self.regular_client.patch(url_admin_poll, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Forbidden

        url_regular_proposal = reverse('poll-detail', args=[self.regular_proposal.id])
        response = self.regular_client.patch(url_regular_proposal, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN) # Forbidden (não pode editar a própria proposta)


    # Testes de Exclusão
    def test_admin_can_delete_any_poll(self):
        """Admin pode excluir qualquer enquete/proposta."""
        url_admin_poll = reverse('poll-detail', args=[self.admin_poll.id])
        response_admin_poll = self.admin_client.delete(url_admin_poll)
        self.assertEqual(response_admin_poll.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Poll.objects.filter(id=self.admin_poll.id).exists())

        url_regular_proposal = reverse('poll-detail', args=[self.regular_proposal.id])
        response_regular_proposal = self.admin_client.delete(url_regular_proposal)
        self.assertEqual(response_regular_proposal.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Poll.objects.filter(id=self.regular_proposal.id).exists())


    def test_regular_user_cannot_delete_poll(self):
        """Usuário comum NÃO pode excluir enquete/proposta (nem mesmo a sua)."""
        url_admin_poll = reverse('poll-detail', args=[self.admin_poll.id])
        response = self.regular_client.delete(url_admin_poll)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        url_regular_proposal = reverse('poll-detail', args=[self.regular_proposal.id])
        response = self.regular_client.delete(url_regular_proposal)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


    # --- Testes de Gerenciamento de Choices (Opções de Voto) ---

    # Testes de Criação
    def test_admin_can_create_choice(self):
        """Admin pode criar uma opção de voto."""
        data = {'poll': self.admin_poll.id, 'choice_text': 'Admin Created Option'}
        response = self.admin_client.post(self.choice_list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Choice.objects.filter(choice_text='Admin Created Option', poll=self.admin_poll).exists())


    def test_regular_user_cannot_create_choice(self):
        """Usuário comum NÃO pode criar opção de voto."""
        data = {'poll': self.admin_poll.id, 'choice_text': 'Regular User Option'}
        response = self.regular_client.post(self.choice_list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Choice.objects.filter(choice_text='Regular User Option').exists())


    # Testes de Atualização/Exclusão
    def test_admin_can_update_choice(self):
        """Admin pode atualizar uma opção de voto."""
        url = reverse('choice_detail_update_delete', args=[self.admin_choice1.id])
        data = {'choice_text': 'Updated Option A'}
        response = self.admin_client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_choice1.refresh_from_db()
        self.assertEqual(self.admin_choice1.choice_text, 'Updated Option A')


    def test_regular_user_cannot_update_choice(self):
        """Usuário comum NÃO pode atualizar opção de voto."""
        url = reverse('choice_detail_update_delete', args=[self.admin_choice1.id])
        data = {'choice_text': 'Attempted Update Option'}
        response = self.regular_client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.admin_choice1.refresh_from_db() # Garantir que não foi alterado
        self.assertNotEqual(self.admin_choice1.choice_text, 'Attempted Update Option')


    def test_admin_can_delete_choice(self):
        """Admin pode excluir uma opção de voto."""
        choice_to_delete = Choice.objects.create(poll=self.admin_poll, choice_text="Temp Choice")
        url = reverse('choice_detail_update_delete', args=[choice_to_delete.id])
        response = self.admin_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Choice.objects.filter(id=choice_to_delete.id).exists())


    def test_regular_user_cannot_delete_choice(self):
        """Usuário comum NÃO pode excluir opção de voto."""
        choice_to_keep = Choice.objects.create(poll=self.admin_poll, choice_text="Another Temp Choice")
        url = reverse('choice_detail_update_delete', args=[choice_to_keep.id])
        response = self.regular_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Choice.objects.filter(id=choice_to_keep.id).exists())


    # --- Testes de Votação ---

    def test_authenticated_user_can_vote(self):
        """Usuário autenticado pode votar em uma enquete ativa."""
        url = reverse('poll-vote', args=[self.admin_poll.id]) # URL da action vote
        data = {'choice': self.admin_choice1.id}
        response = self.regular_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Vote.objects.filter(user=self.regular_user, poll=self.admin_poll, choice=self.admin_choice1).exists())


    def test_user_cannot_vote_twice_on_same_poll(self):
        """Usuário NÃO pode votar duas vezes na mesma enquete."""
        # Primeiro voto
        url = reverse('poll-vote', args=[self.admin_poll.id])
        data1 = {'choice': self.admin_choice1.id}
        response1 = self.regular_client.post(url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Segundo voto na mesma enquete
        data2 = {'choice': self.admin_choice2.id} # Tentando votar em outra opção na mesma enquete
        response2 = self.regular_client.post(url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST) # Deve falhar
        self.assertIn('Você já votou nesta enquete', response2.data.get('non_field_errors', [''])[0]) # Verificar mensagem de erro


    def test_user_cannot_vote_on_inactive_poll(self):
        """Usuário NÃO pode votar em uma enquete inativa."""
        inactive_poll = Poll.objects.create(
            title="Inactive Poll",
            description="This poll is closed.",
            created_by=self.admin_user,
            is_active=False
        )
        inactive_choice = Choice.objects.create(poll=inactive_poll, choice_text="Inactive Option")

        url = reverse('poll-vote', args=[inactive_poll.id])
        data = {'choice': inactive_choice.id}
        response = self.regular_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Não é possível votar em uma enquete inativa', response.data.get('non_field_errors', [''])[0])


    def test_user_cannot_vote_on_expired_poll(self):
        """Usuário NÃO pode votar em uma enquete expirada."""
        expired_poll = Poll.objects.create(
            title="Expired Poll",
            description="This poll has passed its deadline.",
            created_by=self.admin_user,
            deadline=timezone.now() - timedelta(days=1), # Data no passado
            is_active=True # Pode estar ativa mas expirada
        )
        expired_choice = Choice.objects.create(poll=expired_poll, choice_text="Expired Option")

        url = reverse('poll-vote', args=[expired_poll.id])
        data = {'choice': expired_choice.id}
        response = self.regular_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Não é possível votar em uma enquete inativa ou expirada', response.data.get('non_field_errors', [''])[0])


    def test_user_cannot_vote_with_choice_from_different_poll(self):
        """Usuário NÃO pode votar com uma opção de outra enquete."""
        other_poll = Poll.objects.create(
            title="Other Poll",
            description="Different poll.",
            created_by=self.admin_user,
            is_active=True
        )
        other_choice = Choice.objects.create(poll=other_poll, choice_text="Option from other poll")

        url = reverse('poll-vote', args=[self.admin_poll.id]) # Votando na admin_poll
        data = {'choice': other_choice.id} # Usando opção de outra enquete
        response = self.regular_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Esta opção não pertence a esta enquete', response.data.get('choice', [''])[0])


    def test_unauthenticated_user_cannot_vote(self):
        """Usuário não autenticado NÃO pode votar."""
        url = reverse('poll-vote', args=[self.admin_poll.id])
        data = {'choice': self.admin_choice1.id}
        response = self.unauthenticated_client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    # --- Testes de Resultados ---

    def test_authenticated_user_can_view_results(self):
        """Usuário autenticado pode ver resultados."""
        # Registrar alguns votos
        Vote.objects.create(user=self.regular_user, poll=self.admin_poll, choice=self.admin_choice1)
        Vote.objects.create(user=self.admin_user, poll=self.admin_poll, choice=self.admin_choice1) # Admin também pode votar
        user3 = User.objects.create_user(username='user3', password='pass3')
        Vote.objects.create(user=user3, poll=self.admin_poll, choice=self.admin_choice2)

        url = reverse('poll-results', args=[self.admin_poll.id]) # URL da action results
        response_regular = self.regular_client.get(url, format='json')
        self.assertEqual(response_regular.status_code, status.HTTP_200_OK)

        # Verificar a estrutura e contagem dos resultados
        self.assertIsInstance(response_regular.data, list)
        self.assertEqual(len(response_regular.data), 2) # Duas opções com votos

        # Encontrar a opção 1 nos resultados e verificar a contagem
        option1_result = next((item for item in response_regular.data if item['choice_text'] == self.admin_choice1.choice_text), None)
        self.assertIsNotNone(option1_result)
        self.assertEqual(option1_result['vote_count'], 2)

        # Encontrar a opção 2 nos resultados e verificar a contagem
        option2_result = next((item for item in response_regular.data if item['choice_text'] == self.admin_choice2.choice_text), None)
        self.assertIsNotNone(option2_result)
        self.assertEqual(option2_result['vote_count'], 1)


    def test_unauthenticated_user_cannot_view_results(self):
        """Usuário não autenticado NÃO pode ver resultados."""
        url = reverse('poll-results', args=[self.admin_poll.id])
        response = self.unauthenticated_client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)