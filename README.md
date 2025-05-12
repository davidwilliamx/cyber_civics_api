# API Cyber Civics

## Descrição

A API Cyber Civics é o backend do projeto "Cyber Civics", desenvolvida com Django REST Framework. Ela permite o gerenciamento de usuários, a criação e gestão de enquetes e propostas, o registro de votos e a visualização de resultados. A API implementa um sistema de permissões baseado em papéis (Administrador e Usuário Comum) e utiliza autenticação baseada em token.

## Funcionalidades

* **Gerenciamento de Usuários:** Registro e login de usuários.
* **Criação de Enquetes/Propostas:**
    * Administradores podem criar enquetes oficiais.
    * Usuários Comuns podem criar propostas.
* **Gerenciamento de Opções de Voto:** Adição de opções de voto às enquetes/propostas.
* **Votação:** Usuários autenticados podem votar uma vez por enquete/proposta.
* **Visualização de Resultados:** Acesso aos resultados detalhados das votações.
* **Sistema de Permissões:** Diferentes capacidades para Administradores e Usuários Comuns.
* **Autenticação:** Segurança via Token Authentication do Django REST Framework.

## Pré-requisitos

Para interagir com a API, você precisará de um cliente HTTP (como Postman, Insomnia, curl, ou uma aplicação front-end capaz de realizar requisições HTTP).

## Configuração para Uso

### URL Base

Todos os endpoints da API são prefixados com uma URL base.

* **Ambiente de Desenvolvimento Local (Exemplo):** `http://127.0.0.1:8000/api/`
* **Nota:** Esta URL será diferente em ambientes de stage ou produção. Consulte a documentação específica do ambiente.

### Autenticação

A API utiliza Token Authentication.

1.  **Obtenha um Token:** Após o registro ou login bem-sucedido, a API retorna um token de autenticação.
    * Registro: `POST /api/auth/register/`
    * Login: `POST /api/auth/login/`
2.  **Envie o Token:** Para todos os endpoints que requerem autenticação, inclua o token no cabeçalho `Authorization` da requisição:
    ```
    Authorization: Token SEU_TOKEN_AQUI
    ```

## Como Usar

### Papéis e Permissões

Existem dois papéis principais com diferentes níveis de acesso:

* **Usuário Comum:**
    * Registrar-se e fazer login.
    * Listar todas as enquetes/propostas.
    * Ver detalhes de qualquer enquete/proposta.
    * Criar Propostas (com opções padrão "Concordo", "Discordo", "Neutro").
    * Adicionar opções de voto apenas às suas próprias propostas.
    * Votar em enquetes/propostas ativas e não expiradas (um voto por item).
    * Ver resultados de qualquer enquete/proposta.
    * **Não pode:** Criar enquetes oficiais, editar/excluir enquetes/propostas (nem as suas), gerenciar opções de voto de outros (exceto criar para suas propostas).

* **Administrador (`is_staff=True`):**
    * Fazer login.
    * Todas as permissões de um Usuário Comum.
    * Criar Enquetes oficiais (com opções padrão "Concordo", "Discordo", "Neutro").
    * Editar e excluir qualquer enquete ou proposta.
    * Listar, ver detalhes, editar e excluir qualquer opção de voto.
    * Criar opções de voto para qualquer enquete ou proposta.
    * Finalizar enquetes (alterando `is_active` para `false`).

### Endpoints da API

A API retorna respostas no formato JSON.

#### 1. Autenticação e Registro

* **`POST /api/auth/register/`**
    * **Descrição:** Registra um novo usuário comum.
    * **Permissões:** Público.
    * **Request Body (JSON):**
        ```json
        {
            "username": "string",
            "password": "string",
            "email": "string (opcional)"
        }
        ```
    * **Response (201 Created):**
        ```json
        {
            "username": "string",
            "email": "string"
        }
        ```

* **`POST /api/auth/login/`**
    * **Descrição:** Autentica um usuário e retorna um token.
    * **Permissões:** Público.
    * **Request Body (JSON):**
        ```json
        {
            "username": "string",
            "password": "string"
        }
        ```
    * **Response (200 OK):**
        ```json
        {
            "token": "string"
        }
        ```

#### 2. Gerenciamento de Enquetes/Propostas (`/api/polls/`)

* **`GET /api/polls/`**
    * **Descrição:** Lista todas as enquetes e propostas.
    * **Permissões:** Usuário Autenticado.
    * **Response (200 OK):** Array de objetos Poll/Proposal (ver [Estrutura de Dados](#estrutura-de-dados)).

* **`POST /api/polls/`**
    * **Descrição:** Cria uma nova enquete (Admin) ou proposta (Usuário Comum). Opções padrão ("Concordo", "Discordo", "Neutro") são adicionadas automaticamente.
    * **Permissões:** Usuário Autenticado.
    * **Request Body (JSON):**
        ```json
        {
            "title": "string",
            "description": "string",
            "deadline": "datetime or null (opcional)"
        }
        ```
    * **Response (201 Created):** Objeto Poll/Proposal criado (ver [Estrutura de Dados](#estrutura-de-dados)).

* **`GET /api/polls/{id}/`**
    * **Descrição:** Recupera detalhes de uma enquete/proposta específica.
    * **Permissões:** Usuário Autenticado.
    * **Response (200 OK):** Objeto Poll/Proposal (ver [Estrutura de Dados](#estrutura-de-dados)).

* **`PUT /api/polls/{id}/`**
    * **Descrição:** Atualiza completamente uma enquete/proposta.
    * **Permissões:** APENAS Administrador.
    * **Request Body (JSON):**
        ```json
        {
            "title": "string",
            "description": "string",
            "deadline": "datetime or null"
        }
        ```
    * **Response (200 OK):** Objeto Poll/Proposal atualizado.

* **`PATCH /api/polls/{id}/`**
    * **Descrição:** Atualiza parcialmente uma enquete/proposta (ex: `title`, `description`, `deadline`, `is_active`).
    * **Permissões:** APENAS Administrador.
    * **Request Body (JSON):** Campos a serem atualizados.
        ```json
        {
            "title": "Novo título",
            "is_active": false
        }
        ```
    * **Response (200 OK):** Objeto Poll/Proposal atualizado.

* **`DELETE /api/polls/{id}/`**
    * **Descrição:** Exclui uma enquete/proposta.
    * **Permissões:** APENAS Administrador.
    * **Response (204 No Content):** Sucesso na exclusão.

#### 3. Gerenciamento de Opções de Voto (`/api/choices/`)

* **`POST /api/choices/`**
    * **Descrição:** Cria uma nova opção de voto.
    * **Permissões:** Usuário Autenticado.
        * Admin: Pode adicionar a qualquer enquete/proposta.
        * Usuário Comum: Pode adicionar apenas às suas próprias propostas.
    * **Request Body (JSON):**
        ```json
        {
            "poll": "integer (ID da enquete/proposta)",
            "choice_text": "string (texto da opção)"
        }
        ```
    * **Response (201 Created):** Objeto Choice criado (ver [Estrutura de Dados](#estrutura-de-dados)).

* **`GET /api/choices/`**
    * **Descrição:** Lista todas as opções de voto.
    * **Permissões:** APENAS Administrador.
    * **Response (200 OK):** Array de objetos Choice.

* **`GET /api/choices/{id}/`**
    * **Descrição:** Recupera detalhes de uma opção de voto.
    * **Permissões:** APENAS Administrador.
    * **Response (200 OK):** Objeto Choice.

* **`PUT /api/choices/{id}/` e `PATCH /api/choices/{id}/`**
    * **Descrição:** Atualiza uma opção de voto.
    * **Permissões:** APENAS Administrador.
    * **Request Body (JSON):**
        ```json
        {
            "choice_text": "Novo texto da opção"
        }
        ```
    * **Response (200 OK):** Objeto Choice atualizado.

* **`DELETE /api/choices/{id}/`**
    * **Descrição:** Exclui uma opção de voto.
    * **Permissões:** APENAS Administrador.
    * **Response (204 No Content):** Sucesso na exclusão.

#### 4. Votação

* **`POST /api/polls/{id}/vote/`**
    * **Descrição:** Registra um voto em uma enquete/proposta. Um usuário só pode votar uma vez.
    * **Permissões:** Usuário Autenticado.
    * **URL Parameters:** `{id}` - ID da enquete/proposta.
    * **Request Body (JSON):**
        ```json
        {
            "choice": "integer (ID da opção escolhida)"
        }
        ```
    * **Response (201 Created):** Objeto Vote (ver [Estrutura de Dados](#estrutura-de-dados)).

#### 5. Visualização de Resultados

* **`GET /api/polls/{id}/results/`**
    * **Descrição:** Recupera os resultados da votação para uma enquete/proposta.
    * **Permissões:** Usuário Autenticado.
    * **URL Parameters:** `{id}` - ID da enquete/proposta.
    * **Response (200 OK):**
        ```json
        {
            "poll_id": "integer",
            "poll_title": "string",
            "total_votes": "integer",
            "choices_results": [
                {
                    "choice_text": "string",
                    "vote_count": "integer",
                    "percentage": "float"
                }
                // ... mais resultados de opções
            ],
            "is_active": "boolean",
            "deadline": "datetime or null"
        }
        ```

### Estrutura de Dados

Formatos JSON comuns nas respostas da API:

* **Objeto Poll/Proposal:**
    ```json
    {
        "id": "integer",
        "title": "string",
        "description": "string",
        "created_by": "string (username)",
        "created_at": "datetime",
        "deadline": "datetime or null",
        "is_active": "boolean",
        "is_proposal": "boolean",
        "choices": [
            {
                "id": "integer",
                "choice_text": "string"
            }
            // ...
        ]
    }
    ```

* **Objeto Choice:**
    ```json
    {
        "id": "integer",
        "choice_text": "string",
        "poll": "integer (ID da Poll/Proposal associada)"
    }
    ```

* **Objeto Vote (exemplo de retorno ao votar):**
    ```json
    {
        "id": "integer (ID do voto)",
        "choice": "integer (ID da opção votada)",
        "user": "string (username)",
        "voted_at": "datetime"
    }
    ```

* **Objeto Result Item (dentro de `choices_results` em `/api/polls/{id}/results/`):**
    ```json
    {
        "choice_text": "string",
        "vote_count": "integer",
        "percentage": "float"
    }
    ```

### Tratamento de Erros Comuns

A API utiliza códigos de status HTTP padrão. Respostas de erro geralmente incluem detalhes:

* **`400 Bad Request`**: Requisição inválida (dados ausentes, formato incorreto, falha na validação).
    ```json
    {
        "campo_com_erro": ["Mensagem de erro específica."],
        "non_field_errors": ["Mensagem de erro geral."]
    }
    ```
    Exemplos de `non_field_errors`:
    * `"Não é possível votar em uma enquete inativa ou expirada."`
    * `"Você já votou nesta enquete."`

* **`401 Unauthorized`**: Autenticação necessária ou token inválido.
    ```json
    {
        "detail": "Authentication credentials were not provided."
    }
    ```
    ou
    ```json
    {
        "detail": "Invalid token header. No credentials provided."
    }
    ```

* **`403 Forbidden`**: Usuário autenticado não tem permissão para a ação.
    ```json
    {
        "detail": "You do not have permission to perform this action."
    }
    ```
    ou mensagem personalizada como:
    ```json
    {
        "detail": "Você só pode adicionar opções a propostas que você criou."
    }
    ```

* **`404 Not Found`**: Recurso não encontrado.
    ```json
    {
        "detail": "Não encontrado."
    }
    ```

### Conceitos Adicionais

* **Poll vs. Proposal:** Ambos são gerenciados pelo modelo `Poll` no backend. A distinção é feita pelo campo booleano `is_proposal` (`false` para enquetes de Admin, `true` para propostas de Usuários Comuns).
* **Opções (Choices):** Representadas pelo modelo `Choice`, associadas a uma `Poll`. Opções padrão ("Concordo", "Discordo", "Neutro") são adicionadas automaticamente na criação de enquetes/propostas.
* **Votos (Votes):** O modelo `Vote` registra cada voto individual. Garante-se que um usuário pode votar apenas uma vez por enquete/proposta.

## Licença

A licença deste projeto não foi especificada na documentação fornecida.

## Contato / Suporte

Informações de contato ou suporte não foram especificadas na documentação fornecida.