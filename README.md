# 🐄 Gado — Sistema de Gerenciamento de Fazenda

Sistema completo para fazendas de **cria, recria e engorda**, disponível em três interfaces:

| Arquivo | Interface | Requisitos |
|---|---|---|
| `gado.py` | Linha de comando (CLI) | Python 3.6+ |
| `gado_tui.py` | Menus interativos no terminal (TUI) | Python 3.6+ |
| `gado_web/` | Aplicação web com navegador | Python + FastAPI |

Todos compartilham o mesmo banco de dados em `~/.gado.db`.

---

## Instalação

### CLI e TUI (sem dependências externas)

```bash
chmod +x gado.py gado_tui.py

# Alias global (opcional)
alias gado="python3 /caminho/para/gado.py"
alias gado-tui="python3 /caminho/para/gado_tui.py"

# Ou copiar para /usr/local/bin/
cp gado.py /usr/local/bin/gado
cp gado_tui.py /usr/local/bin/gado-tui
```

### Aplicação web

```bash
cd gado_web
pip install fastapi uvicorn jinja2 python-multipart
uvicorn main:app --reload
# Acessar em http://localhost:8000
```

---

## Interface TUI — Menus Interativos

Execute `python3 gado_tui.py` para abrir a interface de menus navegáveis por teclado.

**Controles:**

| Tecla | Ação |
|---|---|
| `↑` `↓` | Navegar no menu / tabela / formulário |
| `Tab` | Próximo campo no formulário |
| `Enter` | Selecionar / confirmar / editar campo |
| `←` `→` | Alternar opções Sim/Não |
| `PgUp` `PgDn` | Rolar tabelas e telas longas |
| `Q` ou `Esc` | Voltar / cancelar |

**Módulos disponíveis na TUI:**

- **Dashboard** — KPIs do rebanho (total ativo, fêmeas, machos, prenhas, saldo) e últimas pesagens
- **Animais** — listar com tabela navegável, cadastrar, buscar por brinco, editar, deletar
- **Pesagem** — registrar pesagem individual com cálculo automático de GMD, histórico por animal
- **Lotes** — listar, criar, ver animais do lote, mover animal entre lotes
- **Pastos** — listar e cadastrar áreas de pastagem
- **Reprodução** — registrar cobertura, diagnóstico de gestação (DG), parto
- **Sanidade** — histórico sanitário, registrar procedimento por animal ou lote inteiro
- **Movimentações** — listar, registrar compra/venda, editar, deletar (valor total calculado automaticamente)
- **Relatórios** — resumo do rebanho, GMD por animal, indicadores reprodutivos, financeiro

**Tela de detalhe do animal** exibe todas as informações em seções com scroll:

- Identificação (brinco, SISBOV, nome)
- Dados zootécnicos (sexo, categoria, raça, nascimento, peso)
- Genealogia (mãe, pai)
- Origem e status (fazenda de origem, datas de entrada e saída)
- Lote atual (nome, fase, pasto)
- Histórico completo de pesagens com GMD entre cada pesagem
- Reprodução — coberturas, DG e partos (para fêmeas)
- Crias cadastradas (para matrizes)
- Últimos 10 procedimentos sanitários
- Movimentações financeiras

---

## Interface CLI — Linha de Comando

### Pastos e Lotes

```bash
gado pasto add --nome "Pasto Norte" --area 50 --forrageira "Brachiaria" --capacidade 60
gado pasto list

gado lote add --nome "Engorda-A" --fase Engorda --pasto "Pasto Norte"
gado lote list
gado lote show --nome "Engorda-A"
gado lote add-animal --lote "Engorda-A" --brinco 005
```

### Animais

```bash
# Cadastrar animal nascido na fazenda
gado animal add --brinco 001 --sexo F --categoria Vaca --raca Nelore --nascimento 2019-03-15

# Cadastrar com genealogia
gado animal add --brinco 003 --sexo M --categoria Bezerro --raca Nelore \
  --mae 001 --pai 002 --peso 35 --nascimento 2024-06-15

# Cadastrar animal comprado (registra movimentação financeira automaticamente)
gado animal add --brinco 010 --sexo F --categoria Novilha --raca Nelore \
  --origem Comprado --peso-entrada 320 --valor-arroba 310 \
  --vendedor "Fazenda Boa Vista" --fazenda-origem "Fazenda Boa Vista"

# Consultar
gado animal list
gado animal list --status Ativo
gado animal list --categoria Novilho
gado animal list --sexo F
gado animal show --brinco 001

# Atualizar
gado animal update --brinco 003 --categoria Novilho
gado animal update --brinco 003 --origem Comprado --fazenda-origem "Fazenda São João"

# Baixa por venda (valor total calculado automaticamente: peso / 15 × R$/@)
gado animal baixa --brinco 004 --tipo venda --peso 480 --valor-arroba 320 \
  --comprador "Frigorífico X" --nf "NF-001234"

# Baixa por morte
gado animal baixa --brinco 010 --tipo morte --causa "Tristeza parasitária"

# Baixa por descarte
gado animal baixa --brinco 011 --tipo descarte

# Deletar cadastro incorreto
gado animal delete --brinco 099
gado animal delete --brinco 099 --force   # apaga mesmo com registros vinculados
```

### Nascimentos

Para registrar um nascimento, combine dois comandos:

```bash
# 1. Cadastrar o bezerro
gado animal add --brinco 005 --sexo M --categoria Bezerro --raca Nelore \
  --nascimento 2024-06-15 --peso 34 --mae 001 --pai 002

# 2. Vincular ao histórico reprodutivo da mãe
gado repro parto --femea 001 --data 2024-06-15 --cria 005
```

### Pesagens

```bash
# Individual (data é opcional — usa a data de hoje se omitida)
gado pesagem add --brinco 004 --peso 350 --fase Engorda
gado pesagem add --brinco 004 --peso 385 --fase Engorda --data 2024-09-01

# Lote inteiro (modo interativo — solicita o peso de cada animal sequencialmente)
gado pesagem lote --lote "Engorda-A" --fase Engorda

# Histórico com GMD calculado entre cada pesagem
gado pesagem historico --brinco 004
```

### Reprodução

```bash
# Registrar cobertura
gado repro add --femea 001 --touro 002 --tipo IATF --data 2024-03-01

# Diagnóstico de gestação
gado repro dg --femea 001 --resultado Positivo --parto-previsto 2024-12-10

# Registrar parto (vincula a cria já cadastrada)
gado repro parto --femea 001 --data 2024-12-08 --cria 003

# Listar coberturas
gado repro list
```

### Sanidade

```bash
# Para lote inteiro
gado sanidade add --lote "Engorda-A" --tipo Vacina --produto "Febre Aftosa" \
  --dose 2 --responsavel "João"

# Para animal individual
gado sanidade add --brinco 001 --tipo Vermífugo --produto "Ivermectina" --dose 5

# Histórico
gado sanidade list
gado sanidade list --brinco 001
```

### Movimentações financeiras

```bash
# Listar (o ID exibido é necessário para editar ou deletar)
gado mov list
gado mov list --brinco 004
gado mov list --tipo Compra

# Registrar compra ou venda avulsa
gado mov add --brinco 004 --tipo Compra --peso 300 --valor-arroba 290 \
  --contraparte "Fazenda São Pedro"

# Editar pelo ID (recalcula valor total automaticamente)
gado mov update --id 2 --peso 310 --valor-arroba 295

# Deletar
gado mov delete --id 2
```

### Relatórios

```bash
gado relatorio rebanho              # Resumo por categoria e sexo
gado relatorio gmd                  # GMD de todos os animais ativos
gado relatorio gmd --fase Engorda   # GMD filtrado por fase
gado relatorio prenhez              # Taxa de prenhez, partos e mortalidade
gado relatorio financeiro           # Compras, vendas e saldo
```

---

## Fases do ciclo produtivo

O sistema usa três fases para classificar lotes e pesagens, refletindo o ciclo completo da pecuária de corte:

**Cria** — do nascimento ao desmame, em torno dos 7-8 meses de idade e 180-200 kg. O foco é na taxa de natalidade e na sobrevivência dos bezerros. Vacas matrizes e touros reprodutores pertencem permanentemente a esta fase.

**Recria** — do desmame até o animal estar pronto para a engorda, geralmente entre 18-24 meses e 280-320 kg. O objetivo é ganho de peso moderado a pasto, preparando o animal para a fase final.

**Engorda** — fase final, onde o animal ganha peso de forma acelerada até o peso de abate, em torno de 480-520 kg (30-35 arrobas). Pode ser conduzida a pasto, em semi-confinamento ou confinamento total. É a fase onde o GMD tem maior impacto no custo por arroba produzida.

Como a fazenda é de **ciclo completo**, o animal passa pelas três fases internamente, o que permite controlar o custo de produção do bezerro ao abate.

### Cadastro de matrizes e reprodutores

Vacas matrizes e touros não transitam pelas fases produtivas — ficam no rebanho de forma permanente. O recomendado é alocá-los em lotes de fase **Cria**:

```bash
gado lote add --nome "Matrizes" --fase Cria --pasto "Pasto Maternidade"
gado lote add --nome "Reprodutores" --fase Cria --pasto "Pasto Touro"

gado lote add-animal --lote "Matrizes" --brinco 001
gado lote add-animal --lote "Reprodutores" --brinco 002
```

---

## Banco de dados

O arquivo `~/.gado.db` (SQLite) é compartilhado entre o CLI, a TUI e a aplicação web. As tabelas são:

- **animal** — cadastro central com genealogia (mãe, pai), origem, status e histórico de saída
- **pasto** — áreas de pastagem com forrageira e capacidade em UA
- **lote** — agrupamentos de animais por fase (Cria, Recria, Engorda)
- **animal_lote** — histórico completo de passagem de cada animal por cada lote
- **pesagem** — histórico de pesos com cálculo automático de GMD
- **reproducao** — ciclo completo: cobertura → DG → parto → cria
- **sanidade** — vacinas, vermífugos, carrapaticidas e exames por animal ou lote
- **movimentacao** — compras e vendas com valor calculado em arrobas
- **mortalidade** — registros de baixa por morte com causa e laudo

```bash
# Backup
cp ~/.gado.db ~/backup-gado-$(date +%Y%m%d).db
```
