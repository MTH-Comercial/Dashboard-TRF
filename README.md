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
