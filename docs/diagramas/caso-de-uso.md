# Diagrama de Caso de Uso

```mermaid
flowchart LR
    dono(["👤 Dono do ambiente"])
    editor(["👤 Parceiro(a)<br/>controle total"])
    leitor(["👤 Convidado<br/>somente leitura"])
    google(["🔐 Google"])

    subgraph DuoCash
        uc1(["Entrar com Google"])
        uc2(["Criar ambiente"])
        uc3(["Gerar convite por link/QR Code"])
        uc4(["Aceitar convite"])
        uc5(["Registrar gasto"])
        uc6(["Editar ou excluir gasto"])
        uc7(["Ver resumo do mês"])
        uc8(["Buscar gastos"])
        uc9(["Remover acesso de membro"])
    end

    dono --> uc1
    dono --> uc2
    dono --> uc3
    dono --> uc5
    dono --> uc6
    dono --> uc7
    dono --> uc8
    dono --> uc9

    editor --> uc1
    editor --> uc4
    editor --> uc5
    editor --> uc6
    editor --> uc7
    editor --> uc8

    leitor --> uc1
    leitor --> uc4
    leitor --> uc7
    leitor --> uc8

    uc1 -.-> google
```

## Descrição resumida

| Caso de uso | Ator | Descrição |
|---|---|---|
| Entrar com Google | Todos | O usuário se autentica com a conta Google. Sem login não acessa nada. |
| Criar ambiente | Dono | Cria um espaço de gastos (ex.: "Casa") e passa a ser o dono dele. |
| Gerar convite | Dono | Escolhe a permissão e o app mostra o QR Code e o link do convite. |
| Aceitar convite | Parceiro(a) / Convidado | Lê o QR Code ou abre o link e entra no ambiente. |
| Registrar gasto | Dono / Parceiro(a) | Informa valor, data, descrição e categoria. |
| Editar ou excluir gasto | Dono / Parceiro(a) | Corrige ou remove um lançamento. |
| Ver resumo do mês | Todos | Vê o total, o gráfico por categoria e quanto cada um gastou. |
| Buscar gastos | Todos | Filtra o extrato por descrição, valor, data, categoria ou autor. |
| Remover acesso de membro | Dono | Tira uma pessoa do ambiente. |
