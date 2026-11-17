# Implantação e instalação do DuoCash

Este guia explica como colocar o DuoCash no ar: o servidor na Google Cloud, o login com Google e o APK nos celulares.

```
Celular (APK)  ──HTTPS──▶  VM Google Cloud  [ Caddy (HTTPS) ─▶ API Flask ─▶ PostgreSQL ]
```

> Nenhuma senha, chave ou segredo fica no repositório. Os segredos do servidor ficam só no arquivo `deploy/.env` da VM, e a chave de assinatura do APK fica só no computador de quem gera o build.

## 1. Servidor na Google Cloud

1. Acesse o [Console da Google Cloud](https://console.cloud.google.com/), crie um projeto (ex.: `duocash`) e ative o faturamento. A VM `e2-micro` entra no nível gratuito nas regiões `us-central1`, `us-east1` e `us-west1`.
2. **Compute Engine → Instâncias de VM → Criar instância**:
   - Nome: `duocash`, região `us-central1`, tipo `e2-micro`;
   - Disco de inicialização: **Debian 12**, 30 GB "disco permanente padrão";
   - Firewall: marque **Permitir tráfego HTTP** e **Permitir tráfego HTTPS**.
3. **Rede VPC → Endereços IP → Reservar endereço estático** e associe à VM (assim o IP não muda).
4. Clique em **SSH** na VM e rode:

   ```bash
   sudo apt-get update && sudo apt-get install -y git
   git clone https://github.com/PAJEGUES/duo-cash.git
   cd duo-cash
   sudo bash deploy/setup-vm.sh
   ```

   O script instala o Docker, cria memória swap, gera as senhas do banco e a chave dos tokens e preenche o endereço do servidor com o IP da VM no formato `34-12-1-9.sslip.io` (HTTPS gratuito, sem precisar comprar domínio).

## 2. Login com Google (OAuth)

No mesmo projeto da Google Cloud:

1. **APIs e serviços → Tela de consentimento OAuth**: tipo **Externo**, nome `DuoCash`, seu e-mail de suporte. Em **Usuários de teste**, adicione o seu e-mail e o da sua esposa (com o app em modo "Teste", só esses e-mails conseguem entrar).
2. **Credenciais → Criar credenciais → ID do cliente OAuth → Aplicativo da Web**. Nome: `DuoCash Web`. Não precisa preencher URIs. Copie o **ID do cliente**.
3. **Criar credenciais → ID do cliente OAuth → Android**:
   - Nome do pacote: `com.pajegues.duocash`
   - Impressão digital SHA-1: a da chave que assina o APK (quem gera o APK obtém com `keytool -list -v -keystore <arquivo>`).
4. Na VM, edite o arquivo de configuração:

   ```bash
   nano ~/duo-cash/deploy/.env
   # GOOGLE_CLIENT_IDS=<id do cliente Web>,<id do cliente Android>
   ```

   O client **Web vem primeiro**. O app busca esse valor no servidor, então não é preciso gerar outro APK se ele mudar.

## 3. Subir a API

```bash
cd ~/duo-cash/deploy
sudo docker compose up -d --build
curl https://$(grep ^DOMAIN= .env | cut -d= -f2)/api/v1/health    # {"status":"ok"}
```

O certificado HTTPS é emitido sozinho na primeira subida (pode levar 1 minuto).

## 4. Instalar o app nos celulares

1. No celular, abra o link do APK da última versão em **[Releases](https://github.com/PAJEGUES/duo-cash/releases)** e baixe `DuoCash.apk`.
2. Toque no arquivo baixado. Se o Android pedir, permita **Instalar apps desconhecidos** para o navegador ou para o app de arquivos.
3. Abra o DuoCash. Na primeira vez, digite o **endereço do servidor** (`https://<ip-com-traços>.sslip.io`) e toque em **Entrar com Google**.
4. Uma pessoa cria o ambiente (ex.: "Casa") e, na aba **Convidar**, gera o QR Code. A outra toca em **Recebi um convite** e aponta a câmera.

## 5. Atualizações

| O que mudou | O que fazer |
|---|---|
| Só o servidor (API) | Na VM: `cd ~/duo-cash && git pull && cd deploy && sudo docker compose up -d --build`. Nada muda nos celulares. |
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
powershell -ExecutionPolicy Bypass -File scripts/build-apk.ps1 -ApiUrl https://<ip-com-traços>.sslip.io
# saída: mobile/dist/DuoCash.apk (+ SHA-256)
```

O parâmetro `-ApiUrl` é opcional: ele só deixa o endereço do servidor preenchido de fábrica.

## 7. Backup do banco

```bash
cd ~/duo-cash/deploy
sudo docker compose exec -T db pg_dump -U duocash duocash | gzip > ~/backup-$(date +%F).sql.gz
```
