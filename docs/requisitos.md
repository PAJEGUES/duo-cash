# Requisitos do DuoCash

## Requisitos funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF01 | O usuário deve entrar no app usando a conta Google | Alta |
| RF02 | O usuário pode criar um ou mais ambientes (ex.: "Casa", "Viagem Chile 2026") | Alta |
| RF03 | O dono do ambiente pode gerar um convite por link ou QR Code | Alta |
| RF04 | No convite o dono escolhe a permissão: controle total ou somente leitura | Alta |
| RF05 | O convidado entra no ambiente lendo o QR Code com a câmera ou abrindo o link | Alta |
| RF06 | O usuário registra um gasto com valor, data, descrição e categoria | Alta |
| RF07 | O sistema grava automaticamente quem foi o autor do gasto | Alta |
| RF08 | Na categoria Lazer o usuário pode escolher um ícone para o gasto | Média |
| RF09 | O usuário pode editar e excluir gastos (se tiver permissão) | Média |
| RF10 | O sistema mostra o total do mês, por categoria e por pessoa | Alta |
| RF11 | O sistema mostra a evolução dos gastos mês a mês | Média |
| RF12 | O usuário pode buscar gastos por descrição, valor, data, categoria e autor | Média |
| RF13 | O dono pode remover o acesso de um membro e cancelar convites | Média |
| RF14 | O dono pode renomear, arquivar ou excluir o ambiente | Baixa |

## Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | O app roda em Android e é distribuído por APK (não vai para a Play Store) |
| RNF02 | Registrar um gasto deve levar menos de 10 segundos |
| RNF03 | Valores são guardados em centavos (número inteiro) para não ter erro de arredondamento |
| RNF04 | A descrição do gasto tem no máximo 100 caracteres, validado no app e no servidor |
| RNF05 | Toda comunicação com o servidor usa HTTPS |
| RNF06 | O app nunca guarda a senha do Google, só os tokens de sessão em armazenamento seguro |
| RNF07 | As permissões são sempre conferidas no servidor, esconder o botão no app não basta |
| RNF08 | O convite só pode ser usado uma vez e expira depois de um tempo |
| RNF09 | Tocar duas vezes em "salvar" não pode gerar gasto duplicado |
| RNF10 | Gastos excluídos não são apagados do banco (exclusão lógica), para manter o histórico |

## Regras do lançamento de gasto

| Campo | Regra |
|---|---|
| Valor | Maior que zero |
| Data | Pode ser retroativa, mas não aceita data futura distante |
| Descrição | Texto livre, até 100 caracteres |
| Categoria | Obrigatória, uma das 17 categorias |
| Ícone | Opcional, sugerido quando a categoria é Lazer |
| Autor | Preenchido pelo servidor, o usuário não escolhe |

## Categorias

As categorias são fixas e o usuário não cria novas. Só a categoria Lazer abre a galeria de ícones.

| # | Categoria | # | Categoria |
|---|---|---|---|
| 1 | Alimentação | 10 | Internet Casa |
| 2 | Saúde | 11 | Taxa INCC |
| 3 | Transporte | 12 | Taxa Evolução de Obra |
| 4 | Educação | 13 | Taxas Inesperadas |
| 5 | Lazer (Diversão) | 14 | Zeca (pet) |
| 6 | Investimentos | 15 | Gasto Desnecessário |
| 7 | Dívidas | 16 | Compras Online |
| 8 | Água e Luz | 17 | Boletos |
| 9 | Internet Pessoal | | |

## Permissões

| Ação | Dono | Controle total | Somente leitura |
|---|:---:|:---:|:---:|
| Ver lançamentos e relatórios | ✅ | ✅ | ✅ |
| Criar lançamento | ✅ | ✅ | ❌ |
| Editar/excluir lançamento | ✅ | ✅ | ❌ |
| Gerar convite (link/QR) | ✅ | ❌ | ❌ |
| Remover acesso de um membro | ✅ | ❌ | ❌ |
| Renomear, arquivar ou excluir o ambiente | ✅ | ❌ | ❌ |

## Ideias para depois

- Foto do comprovante no lançamento
- Orçamento por categoria com alerta quando passar do limite
- Gastos recorrentes (aluguel, internet) lançados automaticamente
- Exportar relatório em PDF e CSV
- Divisão proporcional (quem deve quanto para quem)
- Notificação quando o parceiro registrar um gasto
