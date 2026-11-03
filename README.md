# Dashboard Transforma v2 — Mothé Engenharia

Atualização do dashboard existente no **Streamlit**, preservando a planilha Google Sheets e o endereço já divulgado ao cliente quando o código é publicado na **mesma aplicação**.

## Funcionalidades

- **Visão executiva:** atividades, taxa de resolução, andamento, emergências, prazos vencidos, categorias, início de atividades por mês e metas de visitas.
- **Atividades e projetos:** filtros por base/status/prioridade, busca, descrição e histórico por ID.
- **Visitas e contrato:** metas de **104 visitas Macaé/ano** + **12 visitas Açu/Gradim/ano**; ciclo configurável, regra contra dupla contagem e cronograma de visitas.
- **Planejamento e backlog:** demandas no radar, pendências abertas, atrasos e próximos vencimentos.
- **Diário de bordo:** histórico cronológico por tarefa.
- **Administrador:** criar tarefas, editar tarefas existentes, lançar relatos e atualizar seu status, cadastrar visitas presenciais/remotas e exportar dados.
- **Cliente:** perfil somente leitura, com senha diferente da do administrador.
- **Google Sheets como banco primário:** preserva as duas abas existentes e permite adicionar uma terceira aba dedicada às visitas.

## 1. Antes de publicar — backup e segredos

1. **Faça uma cópia de segurança** do Google Sheets original (Arquivo → Fazer uma cópia).
2. No Google Cloud Console, crie/abra um projeto, habilite **Google Sheets API** e **Google Drive API** ([guia do Google](https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account)), crie uma **conta de serviço** e baixe a chave JSON. Trate a chave como sigilo: não publique no GitHub.
3. Abra sua planilha Google e compartilhe com o e-mail `client_email` da conta de serviço, com permissão **Editor**. Evite publicar sua planilha na Web ou habilitar acesso público por link.
4. Execute `python gerar_senhas.py` uma vez no seu computador (o script solicita uma senha para o cliente e outra para o administrador). Copie os dois *hashes* gerados.
5. Em **Streamlit Community Cloud → seu app → Settings → Secrets** ([documentação oficial](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)), preencha o conteúdo de `.streamlit/secrets.toml.example`, substituindo os placeholders da conta de serviço e os dois hashes. A chave privada deve manter `\n` como na amostra TOML. **Não crie nem comite o arquivo real** `.streamlit/secrets.toml` no GitHub.
6. Configure `CONTRACT_START` com a **data efetiva do início do ciclo de 12 meses**. O valor de exemplo `2026-09-01` foi usado apenas para compatibilidade com o primeiro conjunto de dados (não foi confirmado como data contratual). O painel mostra o ciclo atual automaticamente.

**Ordem sugerida para não interromper o painel:** configure Secrets na aplicação existente antes de alterar o código do repositório.

## 2. Preservar o URL divulgado

Seu código atual está em `MTH-Comercial/Dashboard-TRF`, arquivo `app.py`, ramo `main`, e seu domínio divulgado é `https://dashboard-mth-trf.streamlit.app`.

Para **manter exatamente esse endereço**, atualize os arquivos no **mesmo repositório** e mantenha o aplicativo Streamlit já publicado, sem recriar a aplicação. Envie:

- `app.py` (substitui o atual)
- `analytics.py`, `storage.py`, `security.py`, `gerar_senhas.py`
- `requirements.txt` (substitui o atual)
- `.streamlit/config.toml`
- `.gitignore` e `README.md`

Os arquivos de imagem existentes podem continuar no repositório. Não é preciso alterar a URL. Novos *commits* do GitHub são refletidos automaticamente na aplicação pela hospedagem Streamlit Cloud ([documentação oficial](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)).

**Atenção:** este pacote não foi aplicado automaticamente ao GitHub ou ao app publicado. Publique após revisar os arquivos e configurar Secrets.

## 3. Lançamentos no navegador

Entre com a senha **Administrador** e abra **Gestão administrativa**:

- **Nova atividade:** preencha os dados no formulário; o próximo `ACT-###` é gerado pelo sistema.
- **Editar atividade:** selecione o ID e atualize status, fase, observações, datas etc. A gravação verifica se outra pessoa alterou a linha depois da leitura. Se houve conflito, recarregue.
- **Diário de bordo:** registre o relato com data e vincule-o ao ID. Marque a opção de sincronização para atualizar também fase/status na aba de tarefas.
- **Registrar visita:** no primeiro acesso, execute a migração assistida do histórico, após conferir o backup. Depois disso, registre visitas separadamente das tarefas.

**Contagem de visitas:** inicialmente, enquanto não existe a aba `Visitas_Contrato`, o painel reproduz a abordagem atual (datas nas tarefas, deduplicadas por base/dia), **identificada como provisória**. Ao criar a aba, a origem passa a ser o registro formal de visitas; somente registros `Presencial`, realizados até hoje e dentro do ciclo, entram nas metas. Registros importados são sinalizados para conferência — a migração não comprova que a visita ocorreu.

O lançamento de novas atividades com data de visita **não** cria automaticamente um registro de visita contratual. Se a visita deve entrar na meta, registre também na aba específica. Assim não se conta uma atividade como visita sem comprovação.

## 4. Autenticação e segurança

O aplicativo anterior **embutia uma senha diretamente no código público** e aceitava `?auth=true` como entrada sem validação. A nova versão remove os dois comportamentos. **Troque a senha antiga imediatamente**, pois ela pode permanecer no histórico público do GitHub. Configure um par de senhas novo e forte. Não use os hashes de exemplo.

O método de senha compartilhada com PBKDF2 e papéis separados é adequado a um painel de acesso simples, mas **não substitui SSO/OIDC com identidade individual, auditoria de usuários, MFA e política de permissões corporativas**. Se outras pessoas forem editar, recomenda-se evoluir a autenticação e trilha de auditoria. A escrita é feita com uma única conta de serviço, e o Google Sheets não oferece transações atômicas entre as abas.

**Atenção:** a atualização conjunta do diário e status acontece em duas chamadas Google Sheets. Uma falha após o relato ser salvo pode deixar o status da atividade desatualizado. A interface informa o erro; confira as duas abas antes de reenviar.

## 5. Testar localmente

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

Para visualizar o layout com **dados fictícios**, configure `DEMO_MODE = true` em seu arquivo local de Secrets. Nesse modo a central é só demonstrativa, sem gravação. Não habilite `DEMO_MODE` na produção.

## 6. Esquema existente (mantido)

**Aba de atividades** (`gid=1562629984`):

`ID da Tarefa`, `Data de Início`, `Data da Visita`, `Base`, `Subárea`, `Categoria`, `Descrição`, `Fase`, `Prioridade`, `Previsão de Conclusão`, `Status`, `Pendências/Observações`.

**Aba de diário** (`gid=997870532`):

`Data da Atualização`, `ID da Tarefa`, `Fase Atualizada`, `Status Atualizado`, `Descrição do que aconteceu`.

**Nova aba opcional** `Visitas_Contrato` (criada pelo administrador):

`ID da Visita`, `Data da Visita`, `Base`, `Tipo`, `ID da Tarefa vinculada`, `Resumo`, `Observações`, `Responsável`, `Origem`.

## 7. Auditoria realizada na cópia enviada em 03/11/2026

- 50 atividades válidas e 21 entradas de diário; 39 resolvidas, 9 em andamento, 1 pausada e 1 não iniciada.
- 16 atividades de prioridade emergencial.
- Pelo método antigo, **19 datas/base distintas em Macaé** + **3 no Porto do Açu** = 22 visitas presumidas.
- 8 casos de divergência aparente entre `Fase` e `Status`; isso pode ser intencional, mas precisa de conferência (ex.: tarefa resolvida que permanece com fase de levantamento).
- 43 atividades sem previsão de conclusão (inclui tarefas já resolvidas ou rotineiras, portanto não são necessariamente erros).
- A atividade `ACT-017` consta pausada com prazo de 01/10/2026 na cópia, configurando um alerta de atraso em 03/11/2026.

Esses números são da **cópia XLSX enviada**, e podem não coincidir com dados adicionados posteriormente na planilha online.

## 8. Limitações e próximos passos sugeridos

- Confirmar a **data de início do ciclo contratual**, para evitar percentual enganoso das metas.
- Confirmar se a definição contratual de visita é **uma visita por base/dia**, ou se atendimentos distintos na mesma unidade e dia também devem contar.
- Incluir campos `Data real de conclusão`, `Responsável`, `Horas técnicas`, `Tipo de atendimento` e, opcionalmente, `Fotos/Anexos` em uma revisão futura da planilha. Não foi criado um KPI temporal de conclusão sem essas informações.
- Criar histórico de alterações por usuário ou migrar escrita para banco relacional com autenticação individual se o painel crescer.
