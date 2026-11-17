# Implantação e instalação do DuoCash

Este guia explica como colocar o DuoCash no ar **de graça e para sempre**: a API no Render, o banco no Neon, o login com Google e o APK nos celulares.

```
Celular (APK) ──HTTPS──▶ Render (API Flask, plano Free) ──TLS──▶ Neon (PostgreSQL, plano Free)
       └──── login ────▶ Google OAuth (gratuito)
```

> Nenhuma senha, chave ou segredo fica no repositório. Os segredos ficam só no painel do Render, e a chave de assinatura do APK fica só no computador de quem gera o build.

## Por que Render + Neon (e não Google Cloud)

| Opção | Custo depois do período de teste | Observação |
|---|---|---|
| **Render Free + Neon Free (escolhida)** | **R$ 0, sem prazo** | Nenhum dos dois pede cartão de crédito, então não existe cobrança surpresa. |
| Google Cloud (VM e2-micro) | ~US$ 3,65/mês | Os US$ 300 valem 90 dias. A VM e2-micro continua gratuita depois, mas o IPv4 externo é cobrado (US$ 0,005/h) e é preciso manter um cartão na conta. |
| Oracle Cloud Always Free | R$ 0 | Pede cartão e pode recolher uma VM ociosa (app de duas pessoas fica ocioso quase sempre). |

**Limites do plano gratuito** (sobram para um casal):

- **Render Free:** 512 MB de RAM e 750 horas/mês (dá para ficar ligado o mês inteiro). Depois de **15 minutos sem uso o servidor dorme**; a primeira abertura do app depois disso leva **até ~1 minuto**. O app espera esse tempo sozinho.
- **Neon Free:** 1 GB de dados por projeto (milhões de gastos), banco que "dorme" após 5 minutos sem uso e acorda em menos de 1 segundo. Não há cobrança: se um dia passar do limite, novas gravações falham até liberar espaço.

O **login com Google não depende de hospedagem nem de faturamento**: os IDs de login são criados pelo Firebase, no plano gratuito Spark, sem cartão.

## 1. Banco de dados no Neon

1. Crie uma conta em [neon.com](https://neon.com) (pode entrar com a conta Google; não pede cartão).
2. **New project**: nome `duocash`, Postgres 17, região **AWS US East 1 (N. Virginia)** (a mesma do Render, para a API responder rápido).
3. Em **Connect**, desligue a opção **Connection pooling** e copie a string de conexão. Ela tem este formato:

   ```
   postgresql://<usuário>:<senha>@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```

   Use a conexão **direta** (endereço sem `-pooler`): as migrações do banco rodam a cada deploy e ficam mais seguras sem o pooler. Guarde essa string; ela é a senha do banco.

## 2. Login com Google (pelo Firebase, sem cartão)

O Console da Google Cloud oferece o teste gratuito e pede cartão. O **Firebase** cria o mesmo projeto e os mesmos IDs de login no plano gratuito **Spark**, sem cartão. O app não usa nenhum outro serviço do Firebase.

1. Acesse o [Console do Firebase](https://console.firebase.google.com) com a sua conta Google e clique em **Criar um projeto**. Nome: `duocash`. **Desative o Google Analytics** e clique em **Criar projeto**.
2. No menu da esquerda: **Criação → Authentication → Vamos começar**.
3. Aba **Método de login → Google → Ativar**. Escolha o seu e-mail como e-mail de suporte e clique em **Salvar**.
4. Clique de novo em **Google** e abra **Configuração do SDK da Web**. Copie o **ID do cliente da Web** (termina em `.apps.googleusercontent.com`). **Esse é o valor de `GOOGLE_CLIENT_IDS`** do próximo passo.
5. Clique na engrenagem (**Configurações do projeto**), aba **Geral → Seus apps**, e clique no ícone do **Android**:
   - Nome do pacote: `com.pajegues.duocash`
   - Apelido: `DuoCash`
   - Certificado SHA-1 (da chave que assina o APK oficial):

     ```
     06:F4:A5:0D:4D:54:D3:2C:91:31:76:8C:FB:0C:3F:10:F0:44:67:0B
     ```

   Clique em **Registrar app**. Pule o download do `google-services.json` e os passos do SDK (**Próxima → Próxima → Continuar no console**). O Android não precisa de ID próprio no servidor: ele só precisa estar registrado com esse pacote e esse SHA-1.

Se um dia a chave de assinatura mudar, o novo SHA-1 sai de `keytool -list -v -keystore <arquivo>` e é adicionado em **Configurações do projeto → Seus apps → Adicionar impressão digital**.

O app busca o ID Web no servidor, então mudar essa configuração não exige gerar outro APK.

## 3. API no Render

1. Crie uma conta em [render.com](https://render.com) entrando com o GitHub (não pede cartão).
2. **New → Blueprint**, escolha o repositório `duo-cash`. O Render lê o arquivo [`render.yaml`](../render.yaml) e mostra o serviço `duocash-api` no plano **Free**.
3. Ele pede os dois valores secretos:
   - `DATABASE_URL`: a string de conexão do Neon (passo 1);
   - `GOOGLE_CLIENT_IDS`: o ID do cliente da Web (passo 2).

   A `SECRET_KEY` é gerada pelo próprio Render. O endereço público (`https://duocash-api.onrender.com` ou parecido) é detectado sozinho.
4. Clique em **Apply**. O primeiro deploy leva alguns minutos e cria as tabelas no Neon automaticamente.
5. Teste no navegador: `https://<seu-serviço>.onrender.com/api/v1/health` deve mostrar `{"status":"ok"}`.

O endereço aparece no topo da página do serviço no Render. É ele que vai no app.

## 4. Instalar o app nos celulares

1. No celular, abra o link do APK da última versão em **[Releases](https://github.com/PAJEGUES/duo-cash/releases)** e baixe `DuoCash.apk`.
2. Toque no arquivo baixado. Se o Android pedir, permita **Instalar apps desconhecidos** para o navegador ou para o app de arquivos.
3. Abra o DuoCash. Na primeira vez, digite o **endereço do servidor** (`https://<seu-serviço>.onrender.com`) e toque em **Entrar com Google**. Se o servidor estava dormindo, a primeira resposta pode demorar até 1 minuto.
4. Uma pessoa cria o ambiente (ex.: "Casa") e, na aba **Convidar**, gera o QR Code. A outra toca em **Recebi um convite** e aponta a câmera.

## 5. Atualizações

| O que mudou | O que fazer |
|---|---|
| Só o servidor (pasta `backend/`) | Nada. O Render faz o deploy sozinho a cada push na `main`, e as migrações do banco rodam na subida. Nada muda nos celulares. |
| O app (nova versão em Releases) | Baixar o novo `DuoCash.apk` no celular e instalar por cima. Os dados ficam no servidor, nada se perde. |

Para instalar por cima, o APK precisa ser assinado **sempre com a mesma chave**. Guarde uma cópia de segurança da chave de assinatura fora do computador.

## 6. Gerar o APK (para quem mantém o projeto)

Pré-requisitos no Windows: Node 24, JDK 17 (`winget install Microsoft.OpenJDK.17`) e Android SDK (command-line tools com `platform-tools`, `platforms;android-36` e `build-tools;36.0.0`).

A chave de assinatura fica fora do repositório. Ela é configurada em `~/.gradle/gradle.properties` com estas propriedades:

```
DUOCASH_STORE_FILE=<caminho do .keystore>
DUOCASH_STORE_PASSWORD=...
DUOCASH_KEY_ALIAS=duocash
DUOCASH_KEY_PASSWORD=...
```

```powershell
cd mobile
npm ci
powershell -ExecutionPolicy Bypass -File scripts/build-apk.ps1 -ApiUrl https://<seu-serviço>.onrender.com
# saída: mobile/dist/DuoCash.apk (+ SHA-256)
```

O parâmetro `-ApiUrl` é opcional: ele só deixa o endereço do servidor preenchido de fábrica.

## 7. Backup do banco

O Neon guarda um histórico curto para restauração (**Branches → Restore**). Para uma cópia própria, rode em qualquer computador com o PostgreSQL instalado (versão do `pg_dump` igual ou maior que a do banco):

```bash
pg_dump "<string de conexão do Neon>" | gzip > backup-$(date +%F).sql.gz
```

## Alternativa: servidor próprio (VM)

A pasta [`deploy/`](../deploy) continua disponível para quem quiser rodar tudo numa VM própria (Docker Compose com PostgreSQL, API e Caddy com HTTPS automático via `<ip>.sslip.io`). Numa VM Debian 12:

```bash
sudo apt-get update && sudo apt-get install -y git
git clone https://github.com/PAJEGUES/duo-cash.git && cd duo-cash
sudo bash deploy/setup-vm.sh      # instala Docker, cria swap e gera as senhas no deploy/.env
nano deploy/.env                  # preencha GOOGLE_CLIENT_IDS com o ID Web (e DOMAIN, se não foi detectado)
cd deploy && sudo docker compose up -d --build
```

Atualizar: `cd ~/duo-cash && git pull && cd deploy && sudo docker compose up -d --build`.

Atenção ao custo: na Google Cloud, a VM `e2-micro` (regiões `us-central1`, `us-east1`, `us-west1`, disco "padrão" de até 30 GB) segue gratuita após os 90 dias, mas o **IPv4 externo é cobrado** (~US$ 3,65/mês).
