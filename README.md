# Vagas Litoral Sul

Portal público de **ofertas de emprego dos municípios do Agreste Litoral Sul
potiguar**. É um projeto de extensão do **IFRN Campus Canguaretama**,
desenvolvido e mantido por estudantes do Curso Técnico em Informática.

- **Visitantes** consultam e filtram as vagas abertas (sem login).
- **Empresas** enviam vagas pelo formulário "Divulgue sua vaga" (sem login) e
  acompanham o pedido com um código.
- **Operadores das prefeituras** (com login) cadastram vagas e moderam os
  pedidos **somente do seu município**.
- A **equipe do IFRN** usa o Django Admin, modera qualquer município e vê as
  estatísticas.

---

## 1. Requisitos

- Python **3.12 ou mais recente**
- `pip` e `venv` (já vêm com o Python; no Debian/Ubuntu instale `python3-venv`)
- Única dependência: **Django 5.2 LTS** (ver `requirements.txt`)

## 2. Instalação para desenvolvimento

```bash
# 1) Entre na pasta do projeto
cd vagas_litoral_sul

# 2) Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows (PowerShell ou cmd)

# 3) Instale as dependências
pip install -r requirements.txt

# 4) Crie o arquivo de configuração a partir do exemplo
cp .env.example .env               # Windows: copy .env.example .env

# 5) Crie o banco de dados (também cadastra os 10 municípios e as áreas)
python manage.py migrate

# 6) Crie o usuário administrador (equipe do IFRN)
python manage.py createsuperuser

# 7) (Opcional) Dados de demonstração: operadores e ~20 vagas fictícias
python manage.py popular_demo

# 8) Rode o servidor
python manage.py runserver
```

Acesse:

| Endereço | O que é |
|---|---|
| http://127.0.0.1:8000/ | Portal público |
| http://127.0.0.1:8000/prefeitura/ | Área da prefeitura (login) |
| http://127.0.0.1:8000/admin/ | Django Admin (equipe do IFRN) |
| http://127.0.0.1:8000/widget/ultimas-vagas/ | Widget para `<iframe>` |

### Usuários de demonstração

O comando `popular_demo` cria um operador por município:

| Usuário | Município |
|---|---|
| `operador.ares` | Arês |
| `operador.baiaformosa` | Baía Formosa |
| `operador.canguaretama` | Canguaretama |
| `operador.espiritosanto` | Espírito Santo |
| `operador.goianinha` | Goianinha |
| `operador.montanhas` | Montanhas |
| `operador.pedrovelho` | Pedro Velho |
| `operador.senadorgeorginoavelino` | Senador Georgino Avelino |
| `operador.tibaudosul` | Tibau do Sul |
| `operador.vilaflor` | Vila Flor |

**Senha de todos: `Demo@Vagas2026`** (para trocar: `python manage.py popular_demo --senha OutraSenha`).

> Não rode `popular_demo` em produção.

## 3. Testes automatizados

```bash
python manage.py test
```

Os testes cobrem, entre outros pontos:

- a lista pública esconde vagas **encerradas, expiradas e vencidas** (mesmo sem o cron);
- a empresa envia a solicitação e ela fica **pendente**, com código; honeypot,
  aceite do termo, CNPJ e limite de envios por IP;
- um operador **não vê, não edita, não encerra, não renova e não exclui** vagas
  de outro município, e **não vê nem modera** solicitações de outro município;
- a **aprovação gera a vaga** pública;
- o comando **`expirar_vagas`** (expiração e anonimização LGPD);
- o comando `popular_demo` e a validação de CNPJ (numérico e alfanumérico).

## 4. Estrutura do projeto

```
vagas_litoral_sul/
├── config/            # settings, urls, wsgi e leitor do .env (env.py)
├── vagas/             # área pública + TODOS os modelos
│   ├── models.py      # Municipio, Prefeitura, OperadorPrefeitura, AreaAtuacao, Vaga, SolicitacaoVaga
│   ├── migrations/    # 0002_dados_iniciais cadastra municípios e áreas
│   ├── management/commands/  # expirar_vagas, popular_demo
│   ├── forms.py, views.py, urls.py, admin.py
│   ├── seguranca.py   # anti-spam (hash do IP e limite por hora)
│   └── validadores.py # CNPJ
├── prefeituras/       # área logada (sem modelos próprios)
│   ├── permissoes.py  # @acesso_prefeitura e filtrar_por_municipio()
│   └── forms.py, views.py, urls.py, tests.py
├── templates/         # HTML (Django Templates)
├── static/            # css/ifrn.css, js/acessibilidade.js, img/logo-ifrn-cang.svg
└── deploy/            # exemplos de Nginx e systemd (Gunicorn)
```

**Por que os modelos ficam todos em `vagas/`?** `Vaga` depende de `Municipio`,
e `OperadorPrefeitura` depende de `Prefeitura`, que depende de `Municipio`.
Separar os modelos entre os dois apps criaria importação circular. O app
`prefeituras` contém apenas as telas da área logada.

**Como funciona o isolamento por município:** toda view da prefeitura usa
`@login_required` e `@acesso_prefeitura`. Este decorador descobre o município
do operador, e todas as consultas passam por `filtrar_por_municipio()`. Se um
operador tentar abrir uma vaga de outro município, recebe **404** (nem fica
sabendo que ela existe). Usuários com "Membro da equipe" (`is_staff`) veem todos
os municípios.

## 5. Tarefas administrativas

**Cadastrar um operador de prefeitura (Django Admin):**

1. Em *Vagas Litoral Sul > Prefeituras*, cadastre a prefeitura do município (se ainda não existir).
2. Em *Autenticação e Autorização > Usuários*, crie o usuário. **Não** marque "Membro da equipe".
3. Em *Vagas Litoral Sul > Operadores das prefeituras*, vincule o usuário à prefeitura.

**Desativar um operador:** selecione-o em *Operadores das prefeituras* e use a
ação "Desativar operadores selecionados" (ou desmarque "Ativo" no usuário).

**Incluir outro município:** *Municípios > Adicionar*. Para ocultá-lo do portal,
desmarque "Ativo".

**Equipe do IFRN:** crie o usuário marcando "Membro da equipe" e dê as
permissões necessárias no Admin (ou use `createsuperuser`).

## 6. Publicação em produção sob subcaminho (Gunicorn + Nginx)

Exemplo para publicar em `https://SEU-DOMINIO/vagas/` num servidor
Debian/Ubuntu, com o projeto em `/srv/vagas-litoral-sul`.

### 6.1. Código, ambiente e dependências

```bash
sudo mkdir -p /srv/vagas-litoral-sul
sudo chown $USER /srv/vagas-litoral-sul
# copie o projeto para /srv/vagas-litoral-sul (git clone, scp etc.)
cd /srv/vagas-litoral-sul

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn          # servidor de aplicação (só em produção)
```

### 6.2. Arquivo `.env` de produção

```ini
SECRET_KEY=<gere com: python -c "import secrets; print(secrets.token_urlsafe(50))">
DEBUG=False
ALLOWED_HOSTS=SEU-DOMINIO
CSRF_TRUSTED_ORIGINS=https://SEU-DOMINIO
FORCE_SCRIPT_NAME=/vagas
STATIC_URL=static/
LOGIN_URL=prefeituras:entrar
WIDGET_FRAME_ANCESTORS='self' https://SITE-DO-CAMPUS
LIMITE_SOLICITACOES_POR_HORA=5
CONFIAR_PROXY_REVERSO=True
```

Com `STATIC_URL=static/` (relativo), o Django gera automaticamente os
endereços `/vagas/static/...`. Também descomente, no fim do `config/settings.py`,
as configurações de HTTPS (`SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE` etc.).

### 6.3. Banco, administrador e arquivos estáticos

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput   # copia tudo para staticfiles/
python manage.py check --deploy            # revisa as configurações de segurança

# O Gunicorn roda como www-data e precisa gravar no SQLite
# (no arquivo E na pasta, por causa do arquivo de journal):
sudo chown -R www-data:www-data /srv/vagas-litoral-sul
```

### 6.4. Gunicorn (systemd)

```bash
sudo cp deploy/vagas-litoral-sul.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vagas-litoral-sul
sudo systemctl status vagas-litoral-sul
```

### 6.5. Nginx

Copie os blocos de `deploy/nginx-vagas.conf` para dentro do `server { ... }`
do site do campus e recarregue:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

O ponto principal é este:

```nginx
location /vagas/static/ {
    alias /srv/vagas-litoral-sul/staticfiles/;
}

location /vagas/ {
    proxy_pass http://unix:/run/vagas-litoral-sul/gunicorn.sock:/;  # a "/" final remove o prefixo
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

O Nginx **remove** o `/vagas` antes de repassar a requisição, e o Django o
**recoloca** em todos os links (`{% url %}` e `{% static %}`) por causa de
`FORCE_SCRIPT_NAME=/vagas`. Os cookies também ficam restritos a `/vagas/`.

> Em desenvolvimento (`runserver`), deixe `FORCE_SCRIPT_NAME` vazio.

### 6.6. Widget no site do campus

```html
<iframe src="https://SEU-DOMINIO/vagas/widget/ultimas-vagas/"
        title="Últimas vagas de emprego do Litoral Sul"
        width="100%" height="420" style="border:0"></iframe>
```

Somente essa rota pode ser exibida em `<iframe>`, e apenas pelos sites listados
em `WIDGET_FRAME_ANCESTORS`. O restante do site envia `X-Frame-Options: DENY`.

## 7. Agendar o `expirar_vagas` no cron

O comando marca como expiradas as vagas vencidas e **apaga os dados de contato
das solicitações recusadas há mais de 180 dias** (LGPD). A lista pública já
filtra pela data, então o portal fica correto mesmo se o cron falhar.

```bash
sudo crontab -u www-data -e
```

Adicione a linha (todo dia às 0h10):

```cron
10 0 * * * cd /srv/vagas-litoral-sul && .venv/bin/python manage.py expirar_vagas >> /var/log/vagas-litoral-sul-cron.log 2>&1
```

Crie o arquivo de log com permissão para o `www-data`:

```bash
sudo touch /var/log/vagas-litoral-sul-cron.log
sudo chown www-data:www-data /var/log/vagas-litoral-sul-cron.log
```

## 8. Identidade visual e acessibilidade

- Cores declaradas como variáveis em `static/css/ifrn.css` (`:root`).
- O verde institucional `#32A041` fica no cabeçalho, nas bordas dos cards e em
  detalhes. Botões e links de texto usam o verde-escuro `#1E6B2B`, porque
  branco sobre `#32A041` tem contraste 3,4:1, abaixo do mínimo WCAG AA (4,5:1)
  para texto de tamanho normal.
- Barra gov.br com "Ir para o conteúdo" (atalho Alt+1) e "Alto contraste"
  (preferência guardada no `localStorage`).
- Fonte "Open Sans" quando instalada no aparelho; caso contrário, a fonte do
  sistema. O portal **não** carrega o Google Fonts, para não enviar o IP dos
  visitantes a terceiros.
- O logotipo em `static/img/logo-ifrn-cang.svg` é **provisório**: substitua-o
  pelo oficial, mantendo o mesmo nome de arquivo.

## 9. LGPD em resumo

- Não coletamos dados de candidatos: a candidatura é feita direto com o contratante.
- Das empresas, guardamos apenas o responsável e o contato, com aceite obrigatório do termo.
- O IP de quem envia o formulário não é guardado, apenas um hash (HMAC) dele.
- Dados de contato de solicitações recusadas são apagados após 180 dias (`expirar_vagas`).
- O texto de `templates/vagas/termo.html` é uma base e deve ser revisado pelo
  setor responsável do IFRN antes da publicação.
