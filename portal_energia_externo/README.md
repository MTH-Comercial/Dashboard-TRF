# Portal técnico Transforma — Streamlit

Versão **pública, sem senha**, para consulta externa. Não contém os dados financeiros, faturas originais nem as planilhas brutas do dashboard interno.

## Publicação no Streamlit Community Cloud

- Repositório: `MTH-Comercial/Dashboard-TRF`
- Branch: `portal-energia-externo`
- Main file path: `portal_energia_externo/app.py`
- Visibilidade da aplicação: **Public**

Acesse `https://share.streamlit.io/`, entre com o GitHub e selecione os parâmetros acima em **Create app**. A publicação final exige autorização da conta Streamlit.

## Limitações técnicas

As medições de Bruno (2024) e Jaguar (2026) não são simultâneas; os cenários representam sobreposição hipotética. Os valores MT são históricos jan–ago/2026. Curvas gráficas amostradas; indicadores extraídos dos registros válidos.

## Atualização

Para atualizar a versão externa, substitua somente `portal_energia_externo/dados.json` por uma exportação revisada. **Não** publique o banco interno, faturas PDF ou planilhas XLSX.
