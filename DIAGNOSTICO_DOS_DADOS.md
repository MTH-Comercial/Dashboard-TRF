# Relatório de diagnóstico — Dashboard Transforma

**Fonte:** cópia Excel anexada na conversa, analisada em 03/11/2026. Não é uma leitura em tempo real do Google Sheets.

## Inventário
- 50 atividades válidas e 21 lançamentos do diário de bordo.
- 39 resolvidas; 9 em andamento; 1 pausada/aguardando; 1 não iniciada.
- 16 atendimentos classificados com prioridade Emergencial.
- 19 datas/base em Macaé e 3 em Porto do Açu (método provisório).
- 43 atividades sem previsão de conclusão (nem todas precisam de prazo).

## Pontos para conferência

| ID | Fase atual | Status atual | Avaliação |
|---|---|---|---|
| ACT-004 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-007 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-009 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-014 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-016 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-020 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-022 | Levantamento em Campo | Resolvido | Conferir se o registro está atualizado |
| ACT-035 | Concluído | Em Andamento | Conferir se o registro está atualizado |

## Prazo vencido na cópia

- **ACT-017** — Consultoria sobre compra do gerador e posicionamento: `Pausado`, previsão de conclusão `01/10/2026`. Confirmar se o prazo foi prorrogado, encerrado ou se depende de terceiros.

## Pontos estruturais

1. A métrica de visitas atual deduplica datas por base, mas não comprova realização. Recomenda-se a aba `Visitas_Contrato` com controle separado.
2. O arquivo original não registra a data real de conclusão das tarefas; portanto, não é possível calcular com segurança prazo médio de entrega ou produtividade mensal de tarefas resolvidas.
3. O início exato do ciclo anual deve ser confirmado no contrato, pois o exemplo de 01/09/2026 é provisório.
4. Os dados históricos do diário usam em alguns lançamentos o status `Aguardando Terceiro/Compras`, que difere da lista usada na aba de tarefas (`Aguardando Terceiros`). A nova interface aceita ambos para preservar o histórico.
5. O código antigo contém uma senha em texto puro e um parâmetro de URL que dispensava a conferência de senha; ambos são removidos no código novo. É essencial revogar a senha antiga.
