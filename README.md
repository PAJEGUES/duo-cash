# 💑 DuoCash

Aplicativo de controle financeiro para casais. Os dois registram os gastos no mesmo lugar e acompanham juntos para onde o dinheiro do mês está indo.

> Projeto da disciplina de Engenharia de Software. Por enquanto o repositório tem a documentação e o protótipo das telas, o aplicativo em si ainda não foi desenvolvido.

## 📌 Sobre o Projeto

Quem divide as contas com outra pessoa normalmente controla tudo em planilha, em mensagem de WhatsApp ou de cabeça. Com o tempo ninguém sabe mais quanto foi gasto nem quem pagou o quê.

A ideia do **DuoCash** é ser uma "planilha viva" do casal dentro do celular:

- um dos dois cria um **ambiente** (por exemplo "Casa" ou "Viagem") e convida o outro por **link** ou **QR Code**;
- cada um lança os seus gastos manualmente, com valor, data, descrição e categoria;
- todo lançamento fica marcado com o nome de quem registrou;
- o app soma tudo sozinho e mostra o resumo do mês por categoria e por pessoa.

O app não se conecta com banco nenhum. O registro é 100% manual, que é justamente o que faz o casal prestar atenção no que está gastando.

### Princípios do produto

| Princípio | Na prática |
|---|---|
| Registrar em menos de 10 segundos | Lançamento em uma única tela, começando pelo valor |
| Transparência entre o casal | Todo gasto mostra quem registrou |
| Sem integração bancária | Nada de Open Finance, tudo é digitado pelo usuário |
| Privacidade | Só entra no ambiente quem recebeu convite |
| Funcionar com internet ruim | Cache local e nova tentativa automática de envio |

### Principais funcionalidades

- 🔐 **Login com conta Google**, sem cadastro de senha no app
- 📊 **Ambientes compartilhados**, podendo ter mais de um (Casa, Viagem, Reforma...)
- 📷 **Convite por link ou QR Code**, com permissão de *controle total* ou *somente leitura*
- 💸 **Registro de gastos** com 17 categorias fixas
- 🎨 **Ícones para gastos de lazer** (cinema, restaurante, viagem, show...)
- 📈 **Resumo mensal** com gráfico por categoria e comparativo de quem gastou quanto
- 🔎 **Busca** por descrição, valor, data, categoria e autor

Os requisitos completos estão em [docs/requisitos.md](docs/requisitos.md).
