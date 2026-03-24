

## Projeto de Testes de Carga: Monolítico vs Microsserviços

Este projeto contém três conjuntos de testes de carga para comparar o desempenho entre arquiteturas monolíticas e microsserviços.

### 1. Teste de Carga Simples (`test_load_1`)
Utiliza o K6 para simular requisições alternadas entre POST e GET para o endpoint `/transactions` (`http://localhost:30090/transactions`).
**Configuração dos stages:**
- 1 requisição a cada 10s por 1 minuto
- 10 requisições a cada 10s por 30 segundos
- 1 requisição a cada 10s por 2 minutos
- 10 requisições a cada 10s por 3 minutos
- 1 requisição a cada 10s por 30 segundos
**Métodos:** POST (criação de transação) e GET (consulta de transações)
**Total de requisições:** depende da configuração dos stages, alternando POST e GET.
**Resultados:** CPU e memória em CSV/JSON, gráficos gerados pelo script `generate_load_graphs1.py`.

### 2. Teste Estruturado (`test_load_2`)
Foram enviadas exatamente 300 requisições (POST e GET alternados) durante 10 minutos para o endpoint `/transactions` (`http://localhost:30090/transactions`).
**Configuração:**
- 300 requisições distribuídas ao longo de 10 minutos 
- Métodos: POST (criação) e GET (consulta)
- Endpoint: `/transactions`
**Resultados:** Respostas salvas em arquivos JSON na pasta `input-datas`. Gráficos gerados pelo script `generate_load_graphs2.py`.

### 3. Teste Gradual (`test_load_3`)
Aplica carga progressiva para observar a degradação sob estresse.
**Configuração:**
- Fase única: 15.000 requisições por 1 minuto (250 req/s)
- Endpoints:
	- Microsserviços: `/transactions/1` e `/accounts` (portas 30090 e 62371)
	- Monolítico: `/transactions/1` e `/accounts` (porta 55111)
- Métodos: GET
**Resultados:** Respostas salvas em arquivos JSON na pasta `Inputs-data`. Gráficos gerados pelo script `generate_gradual_graphs.py`.

Cada pasta contém scripts para geração de gráficos e os dados de entrada/saída dos testes.
