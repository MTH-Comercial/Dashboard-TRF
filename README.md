# Dashboard Transforma V4 | Mothé Engenharia

Versão de testes do painel do contrato Transforma, com separação clara entre **presença contratual**, **entregas de engenharia**, **registros de rotina**, **reuniões** e **demandas no radar**.

## O que mudou

1. A visão executiva começa pelo cumprimento do contrato, incluindo visitas presenciais de rotina, emergenciais, reuniões, levantamentos e acompanhamentos. Uma visita por **base e data**, independente de quantas atividades tenham ocorrido naquele dia.
2. Os indicadores de engenharia excluem visitas de rotina, reuniões e registros apenas de acompanhamento, sem perder essas informações no histórico.
3. A visão executiva usa cartões compactos com legendas internas. As seções de entregas concluídas e prioridades abertas têm rolagem interna, mostrando aproximadamente cinco linhas simultaneamente.
4. A navegação **Histórico de atividades** substitui o nome Diário de bordo; a aba **Atualizacoes** continua recebendo o mesmo histórico com alterações sucessivas de fase e status. A variação histórica é normal, não um erro.
5. O erro `KeyError: Data de Início_dt` foi corrigido tratando os resultados vazios antes de ordenar.
6. As visitas e reuniões antigas com status `Resolvido` aparecem como `Realizada` na interface sem alterar os dados históricos. Novos lançamentos podem ter status `Realizado`.
7. A aba `Visitas_Contrato` aceita **Finalidade** e **Validação**. Registros migrados são `A validar`; podem ser revisados antes da publicação, e `Descartada` é excluída da contagem.

## Nova planilha migrada

O arquivo `Transforma_Base_Migrada_Dashboard_V4.xlsx` criado a partir do Excel do usuário de 04/11/2026 contém:

- `Atividades`: 52 registros (50 existentes e dois registros sem ID que receberam `ACT-051` e `ACT-052`). Mantém as 12 colunas históricas mais `Tipo de Registro`, `Condição do Prazo` e `Motivo de Espera`.
- `Atualizacoes`: 21 eventos do histórico antigo; **não corrige nem descarta** alterações de fase.
- `Visitas_Contrato`: 22 visitas presenciais *estimadas* com uma linha por base/data. Inclui finalidade preliminar e validação `A validar`. A existência de um registro na antiga planilha não comprova a visita; conferir antes de uso externo.
- `Configuracao` e `Instrucoes`: premissas e orientações.

**Importante:** não disponibilizar a planilha do cliente no GitHub público. Ela é entregue separadamente, para importação em um **Google Sheets privado**. Não sobrescrever a planilha antiga; manter cópia de segurança.

## Acessar os dados na versão de teste

1. Acesse o app de teste `https://dashboard-transforma-v2-teste.streamlit.app` e entre em demonstração.
2. Abra `📁 Dados de teste / Importar Excel` na barra lateral.
3. Selecione `Transforma_Base_Migrada_Dashboard_V4.xlsx`.
4. Serão exibidos os dados históricos e o controle de visitas completo; as alterações feitas pela interface são temporárias e não alteram o Google Sheets.

## Conectar a base nova na versão definitiva

Crie uma planilha Google Sheets **nova**, importando o arquivo XLSX migrado, e copie seu `spreadsheetId`. A aplicação prefere as abas por nome, mas ainda consegue carregar a planilha antiga por `gid`, preservando a compatibilidade:

- `Atividades` (novo) / `gid=1562629984` (antigo)
- `Atualizacoes` (novo) / `gid=997870532` (antigo)
- `Visitas_Contrato`

No Streamlit Community Cloud → App → Settings → Secrets, configure os valores necessários:

```toml
SHEET_ID = "COLOQUE_O_ID_DA_NOVA_PLANILHA"
CONTRACT_START = "2026-09-01" # Provisório: conferir início do contrato
CLIENT_PASSWORD_HASH = "..."
ADMIN_PASSWORD_HASH = "..."

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Crie contas de senha novas e compartilhe **apenas a planilha nova** com o e-mail da conta de serviço como Editor. Não exponha Secrets nem credenciais no GitHub. A cópia de teste continua em `DEMO_MODE = true`; antes da operação definitiva configure `DEMO_MODE = false` e teste o login de administrador e consulta.

A versão pública do cliente continua em `main` até aprovação do painel e da conexão Google.

## Testes

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m compileall -q app.py analytics.py storage.py preview.py
```

16 testes unitários passaram localmente. A escrita real depende de uma conta de serviço configurada em Secrets; o teste end-to-end de gravação no Google ainda é pendente.

## Relato geral de cada visita (V5)

A aba privada `Visitas_Contrato` mantém **uma visita por base/data** para o controle contratual, mas sua coluna **`Observações`** agora também é o **relato geral da visita**. Nela devem constar orientação rápida, consultoria informal, reunião e acompanhamento técnico feitos no dia, mesmo que nenhuma dessas ocorrências justifique abrir uma tarefa ACT.

- **Atividade técnica:** representa a demanda/entrega com status e histórico próprios.
- **Visita contratual:** registra a presença na unidade, independentemente da finalidade. Uma visita pode envolver várias atividades e orientações breves.
- **Resumo:** assunto principal em uma linha; **Observações:** relato narrativo do dia, mais completo.
- **Origem / Validação:** preservam a rastreabilidade das visitas migradas. `A validar` não equivale a visita confirmada documentalmente.

O formulário **Gestão administrativa → Registrar visita** oferece dois fluxos: **Registrar nova visita** e **Complementar / validar visita existente**. Editar o relato não altera a data/base nem acrescenta uma visita aos indicadores. Na aba **Visitas e contrato**, é possível selecionar uma visita para ler o texto do dia.

Na migração automática de uma planilha antiga, o sistema dá preferência à anotação da atividade **Visita de rotina** da mesma base/data, copiando seu texto original, sem inventar acontecimentos nem apagar as anotações das tarefas. Registros já existentes em `Visitas_Contrato` não são reescritos automaticamente; a revisão deles é feita individualmente na área administrativa.

## V6 — separar atividades ACT de visitas contratuais VIS

**Regra de cadastro:** `ACT-xxx` identifica **serviço, projeto, demanda técnica ou reunião independente**. Toda visita às unidades, incluindo rotina, emergência, acompanhamento e levantamento, é cadastrada exclusivamente em `Gestão administrativa → Registrar visita` e recebe `VIS-xxxx`. O mesmo dia pode ter um VIS geral com vários serviços ACT vinculados, mas não se abre ACT apenas para relatar a presença em campo.

A interface de `Lançar trabalho do dia` permite escolher entre atualizar ACT, criar ACT ou registrar VIS. O backend bloqueia a criação de ACT com tipo visita ou com descrição iniciada por “Visita”. Na seção `Atividades e projetos`, visitas históricas também são excluídas da lista de atividades; o detalhamento delas pertence à página `Visitas e contrato`.

### Migração segura da base V5 para V6

A planilha `Base_Transforma_V6_Atividades_e_Visitas_Separadas.xlsx` foi gerada **fora do GitHub público**, preservando os relatos históricos:

- `Atividades`: 29 registros que não representam visitas, mantendo seus IDs ACT originais; a sequência terá lacunas, intencionalmente.
- `Visitas_Contrato`: 22 visitas já registradas, cada qual com o identificador VIS; a mesma ida presencial não aparece novamente como ACT. Os campos `Resumo`, `Observações` e `Validação` permanecem.
- `Atualizacoes`: 20 atualizações vinculadas a ACT ativos.
- `Arquivo_ACT_Visitas`: 23 ACT históricos de visita, preservados para auditoria com referência ao VIS correspondente; o antigo ACT-043 não tem data de visita confirmada e está indicado como pendente, **sem criar um VIS fictício**.
- `Arquivo_Atualizacoes_VIS`: 1 atualização histórica originalmente associada à visita ACT-045. Seu conteúdo foi incorporado ao relato geral VIS correspondente e preservado integralmente no arquivo de auditoria.
- `Instrucoes` e `Configuracao`: regras de uso e conferência.

**Não subir o arquivo de cliente no GitHub público.** Faça backup, importe a V6 no ambiente demonstrativo e confira os registros. Somente após aprovação, crie uma base **privada** em Google Sheets e direcione `SHEET_ID` nas Secrets do Streamlit para esse novo arquivo. Os registros de visita `A validar` devem ser revisados documentalmente antes do uso contratual.

Compatibilidade: o importador agora dá preferência às abas oficiais `Atividades`, `Atualizacoes` e `Visitas_Contrato`, ignorando arquivos históricos como fontes para os indicadores. O repositório e a hospedagem de produção original do cliente continuam intocados durante o teste.

## Base oficial para TESTES — Google Sheets V6 (04/11/2026)

A nova planilha está criada **na mesma pasta `04 Transforma (R.R)` da base antiga**, como Google Sheets nativo:

- ID: `1_KEm7fLJpglz89vG-67hXIKrWOVSpcEkUXNILbSF1QE`
- URL: https://docs.google.com/spreadsheets/d/1_KEm7fLJpglz89vG-67hXIKrWOVSpcEkUXNILbSF1QE/edit
- Abas: `Atividades` (29 registros ACT), `Visitas_Contrato` (22 VIS), `Atualizacoes` (20 eventos), `Arquivo_ACT_Visitas` (23 registros), `Arquivo_Atualizacoes_VIS` (1 evento), `Instrucoes` e `Configuracao`.
- Os valores foram conferidos após a criação da planilha nativa. A base anterior **não** foi substituída, e a V6 é privada.

O código da **branch de teste** tem esse ID como `DEFAULT_SHEET_ID` e **recusa conectar-se a uma planilha diferente**, prevenindo edição acidental da base antiga. A branch `main` do cliente permanece intacta.

### Falta autorizar o Streamlit de teste

1. Na [aplicação de teste](https://dashboard-transforma-v2-teste.streamlit.app), abra **Manage app → Settings → Secrets**. Não publique credenciais no GitHub.
2. Faça backup dos secrets atuais. Configure `SHEET_ID = "1_KEm7fLJpglz89vG-67hXIKrWOVSpcEkUXNILbSF1QE"` e `[gcp_service_account]` com credenciais próprias, **sem copiá-las para o código**.
3. Compartilhe **somente a planilha V6** com o `client_email` da conta de serviço Google como **Editor**. Use o Drive para conceder o acesso. Não use a opção pública “Qualquer pessoa com o link”.
4. Configure `ADMIN_PASSWORD_HASH` e `CLIENT_PASSWORD_HASH` com valores gerados por `gerar_senhas.py`. Enquanto `DEMO_MODE = true`, qualquer pessoa consegue usar a demonstração como administrador **sem gravação real**.
5. **Somente depois** de configurar e conferir senhas e conta de serviço, altere `DEMO_MODE = false`. Reboot no Streamlit, faça login administrativo, confira 29 ACT, 22 VIS e 20 eventos e teste um lançamento de baixa criticidade.

**Atenção:** alterar `DEFAULT_SHEET_ID` no GitHub não altera os `Secrets` de um aplicativo já implantado; o Streamlit pode continuar mostrando a demonstração até que a configuração acima seja concluída. A conexão Google não foi validada de ponta a ponta enquanto essas credenciais privadas não estiverem configuradas.
