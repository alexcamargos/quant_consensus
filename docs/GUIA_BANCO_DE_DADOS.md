# Guia de Acesso e Uso do Banco de Dados (DuckDB)

O projeto **QuantConsensus** utiliza o [DuckDB](https://duckdb.org/) como motor analítico e Data Warehouse local. O DuckDB foi escolhido por ser um banco de dados relacional embarcado voltado nativamente para processamento colunar e análises analíticas (OLAP), oferecendo excelente performance em consultas pesadas.

O arquivo do banco de dados de produção é gerado automaticamente na pasta `data/` do projeto com o nome:
`data/quant_consensus_prod.duckdb`

---

## 1. Como acessar o Banco de Dados

### Via Cliente SQL (DBeaver, DataGrip, etc.)
A forma mais amigável de visualizar tabelas, views e rodar querys manuais é usar uma IDE de banco de dados.

**No DBeaver:**
1. Clique em **Nova Conexão**.
2. Selecione **DuckDB**.
3. No campo `Path`, aponte para o arquivo `data/quant_consensus_prod.duckdb` na pasta do seu projeto.
4. Clique em **Concluir** e expanda a conexão para ver as views e tabelas.

### Via Python
Como o DuckDB roda localmente em processo, é possível conectar facilmente através de qualquer script Python ou Jupyter Notebook:

```python
import duckdb
import pandas as pd

# Conecta ao arquivo (cria se não existir)
conn = duckdb.connect('data/quant_consensus_prod.duckdb')

# Executa uma query e retorna direto como um DataFrame do Pandas
df = conn.execute("SELECT * FROM vw_carteira_consolidada WHERE mes_ref = '2026-08'").df()
print(df)
```

### Via Linha de Comando (CLI)
Se você tiver a CLI do DuckDB instalada, basta abrir o terminal na pasta do projeto e rodar:
```bash
duckdb data/quant_consensus_prod.duckdb
```
E você poderá rodar os comandos SQL diretamente no terminal.

---

## 2. Estrutura do Banco de Dados

O banco armazena as recomendações cruas e contém várias **Views** prontas (tabelas virtuais) para facilitar as análises sem precisar escrever queries complexas. 

### Tabelas Físicas
- `raw_recomendacoes`: Tabela principal com todas as recomendações extraídas do site (contém as colunas `corretora`, `ticker` e `mes_ref`).
- `dados_mercado`: Tabela mockada atualmente, utilizada para simular dados de volume médio financeiro usados em desempates.

### Views Analíticas (Prontas para uso)

Você pode acessar os dados das seguintes views como se fossem tabelas comuns usando `SELECT * FROM <nome_da_view>`.

#### `vw_corretoras_por_mes`
Lista as corretoras acompanhadas em cada mês de referência. Útil para auditoria e conferência se todas as casas de análise publicaram suas carteiras no período.
- **Colunas:** `mes_ref`, `total_corretoras`, `lista_corretoras`
- **Exemplo:** `SELECT * FROM vw_corretoras_por_mes;`

#### `vw_dados_corretoras`
Extrato linear de cada papel recomendado por cada corretora.
- **Colunas:** `mes_ref`, `corretora`, `ticker`
- **Exemplo:** `SELECT * FROM vw_dados_corretoras WHERE corretora = 'XP Investimentos';`

#### `vw_carteira_consolidada`
Apresenta o ranking (Top 10) dos papéis mais recomendados de cada mês de forma já consolidada, aplicando o desempate pelo volume de negociação.
- **Colunas:** `mes_ref`, `rank`, `ticker`, `votos`, `volume_desempate`
- **Exemplo:** `SELECT * FROM vw_carteira_consolidada WHERE mes_ref = '2026-08';`

#### `vw_alteracoes_carteira`
Mapeia a movimentação (Momentum) das corretoras mês a mês, identificando quais ações elas adicionaram (Entrada), removeram (Saída) ou mantiveram (Manutenção) na carteira em relação ao mês imediatamente anterior em que participaram.
- **Colunas:** `mes_ref`, `corretora`, `ticker`, `status`
- **Exemplo:** `SELECT * FROM vw_alteracoes_carteira WHERE status = 'Entrada' AND mes_ref = '2026-08';`
