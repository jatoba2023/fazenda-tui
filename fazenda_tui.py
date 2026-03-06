#!/usr/bin/env python3
"""
fazenda-tui — Sistema de Gestão da Fazenda
Interface de menus navegáveis por teclado
Módulos: Gado · Eucalipto · Financeiro · Equipamentos
"""

import sys
if sys.platform == "win32":
    import windows_curses  # pip install windows-curses
import curses
import sqlite3
import os
from datetime import date, datetime

# ─────────────────────────────────────────────
# CAMINHO DO BANCO — migra automaticamente
# ─────────────────────────────────────────────
OLD_DB = os.path.expanduser("~/.gado.db")
DB_PATH = os.path.expanduser("~/.fazenda.db")

def migrate_db_path():
    if not os.path.exists(DB_PATH) and os.path.exists(OLD_DB):
        os.rename(OLD_DB, DB_PATH)

# ─────────────────────────────────────────────
# BANCO DE DADOS
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    -- ── GADO ──────────────────────────────────────
    CREATE TABLE IF NOT EXISTS pasto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE, area_ha REAL,
        forrageira TEXT, capacidade_ua INTEGER, observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS animal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brinco TEXT NOT NULL UNIQUE, sisbov TEXT, nome TEXT,
        sexo TEXT CHECK(sexo IN ('M','F')) NOT NULL,
        categoria TEXT CHECK(categoria IN ('Bezerro','Bezerra','Novilho','Novilha','Vaca','Touro','Boi')) NOT NULL,
        raca TEXT, data_nascimento TEXT, peso_nascimento REAL,
        id_mae INTEGER REFERENCES animal(id),
        id_pai INTEGER REFERENCES animal(id),
        origem TEXT CHECK(origem IN ('Nascido','Comprado')) DEFAULT 'Nascido',
        fazenda_origem TEXT,
        status TEXT CHECK(status IN ('Ativo','Vendido','Morto','Descartado')) DEFAULT 'Ativo',
        data_entrada TEXT DEFAULT (date('now')),
        data_saida TEXT, observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS lote (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        fase TEXT CHECK(fase IN ('Cria','Recria','Engorda')) NOT NULL,
        id_pasto INTEGER REFERENCES pasto(id),
        data_inicio TEXT DEFAULT (date('now')),
        data_fim TEXT, observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS animal_lote (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        id_lote INTEGER NOT NULL REFERENCES lote(id),
        data_entrada TEXT DEFAULT (date('now')), data_saida TEXT
    );
    CREATE TABLE IF NOT EXISTS pesagem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        data_pesagem TEXT NOT NULL DEFAULT (date('now')),
        peso_kg REAL NOT NULL,
        fase TEXT CHECK(fase IN ('Cria','Recria','Engorda')), observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS reproducao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_femea INTEGER NOT NULL REFERENCES animal(id),
        id_touro INTEGER REFERENCES animal(id),
        tipo TEXT CHECK(tipo IN ('Monta Natural','IA','IATF')) DEFAULT 'Monta Natural',
        data_cobertura TEXT, data_dg TEXT,
        resultado_dg TEXT CHECK(resultado_dg IN ('Positivo','Negativo','Vazia')),
        data_parto_previsto TEXT, data_parto_real TEXT,
        id_cria INTEGER REFERENCES animal(id), observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS sanidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER REFERENCES animal(id),
        id_lote INTEGER REFERENCES lote(id),
        data TEXT NOT NULL DEFAULT (date('now')),
        tipo TEXT CHECK(tipo IN ('Vacina','Vermífugo','Carrapaticida','Exame','Outro')) NOT NULL,
        produto TEXT, dose_ml REAL, lote_produto TEXT, responsavel TEXT, observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS movimentacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        tipo TEXT CHECK(tipo IN ('Compra','Venda')) NOT NULL,
        data TEXT NOT NULL DEFAULT (date('now')),
        peso_kg REAL, valor_arroba REAL, valor_total REAL,
        contraparte TEXT, nota_fiscal TEXT, observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS mortalidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        data TEXT NOT NULL DEFAULT (date('now')), causa TEXT, laudo TEXT
    );

    -- ── FINANCEIRO ────────────────────────────────
    CREATE TABLE IF NOT EXISTS fin_conta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        banco TEXT,
        agencia TEXT,
        numero TEXT,
        saldo_inicial REAL NOT NULL DEFAULT 0,
        ativa INTEGER NOT NULL DEFAULT 1,
        observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS fin_lancamento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data TEXT NOT NULL DEFAULT (date('now')),
        data_pagamento TEXT,
        tipo TEXT CHECK(tipo IN ('Receita','Despesa')) NOT NULL,
        valor REAL NOT NULL,
        descricao TEXT NOT NULL,
        categoria TEXT CHECK(categoria IN ('Gado','Eucalipto','Equipamento','Geral')) NOT NULL DEFAULT 'Geral',
        id_conta INTEGER REFERENCES fin_conta(id),
        status TEXT CHECK(status IN ('Previsto','Realizado')) NOT NULL DEFAULT 'Previsto',
        origem TEXT,
        id_origem INTEGER,
        observacao TEXT
    );

    -- ── EUCALIPTO ─────────────────────────────────
    CREATE TABLE IF NOT EXISTS eu_safra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        descricao TEXT,
        data_inicio TEXT,
        data_fim TEXT,
        status TEXT CHECK(status IN ('Ativa','Concluída','Planejada')) DEFAULT 'Planejada',
        observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS eu_talhao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        area_ha REAL NOT NULL,
        data_plantio TEXT,
        clone TEXT,
        status TEXT CHECK(status IN ('Crescendo','Colhido','Reforma','Inativo')) DEFAULT 'Crescendo',
        observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS eu_curva_crescimento (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idade_meses INTEGER NOT NULL UNIQUE,
        volume_m3_ha REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS eu_mov_talhao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_talhao INTEGER NOT NULL REFERENCES eu_talhao(id),
        data TEXT NOT NULL DEFAULT (date('now')),
        tipo TEXT CHECK(tipo IN ('Adubação','Formicida','Desbrota','Calagem','Herbicida','Outro')) NOT NULL,
        produto TEXT,
        quantidade TEXT,
        custo REAL,
        id_conta INTEGER REFERENCES fin_conta(id),
        data_pagamento TEXT,
        id_lancamento INTEGER REFERENCES fin_lancamento(id),
        responsavel TEXT,
        observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS eu_carga (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_safra INTEGER NOT NULL REFERENCES eu_safra(id),
        numero TEXT,
        data_corte TEXT,
        data_saida TEXT,
        data_romaneio TEXT,
        volume_m3 REAL,
        valor_unitario REAL,
        valor_total REAL,
        data_recebimento TEXT,
        id_conta INTEGER REFERENCES fin_conta(id),
        id_lancamento INTEGER REFERENCES fin_lancamento(id),
        status TEXT CHECK(status IN ('Pendente','Romaneio','Recebida')) DEFAULT 'Pendente',
        observacao TEXT
    );

    -- ── EQUIPAMENTOS ──────────────────────────────
    CREATE TABLE IF NOT EXISTS equip_item (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        tipo TEXT CHECK(tipo IN ('Trator','Implemento','Veículo','Outro')) NOT NULL,
        marca TEXT,
        modelo TEXT,
        ano INTEGER,
        numero_serie TEXT,
        valor_aquisicao REAL,
        data_aquisicao TEXT,
        id_conta INTEGER REFERENCES fin_conta(id),
        status TEXT CHECK(status IN ('Ativo','Vendido','Sucata')) DEFAULT 'Ativo',
        observacao TEXT
    );
    CREATE TABLE IF NOT EXISTS equip_manutencao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_equip INTEGER NOT NULL REFERENCES equip_item(id),
        data TEXT NOT NULL DEFAULT (date('now')),
        tipo TEXT CHECK(tipo IN ('Preventiva','Corretiva','Revisão')) NOT NULL,
        descricao TEXT,
        custo REAL,
        prestador TEXT,
        id_conta INTEGER REFERENCES fin_conta(id),
        data_pagamento TEXT,
        id_lancamento INTEGER REFERENCES fin_lancamento(id),
        observacao TEXT
    );
    """)

    # Migrations para colunas novas em tabelas existentes
    def add_col(table, col, typedef):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typedef}")

    add_col("animal",           "fazenda_origem",  "TEXT")
    add_col("movimentacao",     "id_lancamento",   "INTEGER REFERENCES fin_lancamento(id)")
    add_col("movimentacao",     "id_conta",        "INTEGER REFERENCES fin_conta(id)")
    add_col("movimentacao",     "status_fin",      "TEXT")
    add_col("equip_item",       "numero_serie",    "TEXT")
    add_col("equip_manutencao", "subcategoria",      "TEXT")
    add_col("eu_despesa_safra", "fornecedor",        "TEXT")
    add_col("fin_lancamento",   "beneficiario",      "TEXT")
    add_col("eu_carga",         "placa",             "TEXT")
    add_col("eu_carga",         "tipo_carga",        "TEXT")
    add_col("eu_carga",         "nome_cliente",      "TEXT")
    add_col("eu_carga",         "codigo_romaneio",   "TEXT")
    add_col("eu_carga",         "preco_m3",          "REAL")
    add_col("eu_carga",         "desconto",          "REAL")
    add_col("eu_carga",         "percentual_recebido","REAL")
    add_col("eu_carga",         "valor_recebido",    "REAL")
    add_col("eu_carga",         "valor_total",       "REAL")
    add_col("eu_carga",         "percentual_recebido","REAL")
    add_col("eu_carga",         "desconto",          "REAL")
    add_col("eu_carga",         "valor_recebido",    "REAL")
    # Migrate old status values to new set
    conn.execute("UPDATE eu_carga SET status='Pendente' WHERE status IN ('Cortada','Saiu')")
    conn.execute("UPDATE eu_carga SET status='Romaneio' WHERE status='Romaneio'")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS eu_despesa_safra (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            id_safra    INTEGER NOT NULL REFERENCES eu_safra(id),
            data        TEXT NOT NULL DEFAULT (date('now')),
            categoria   TEXT CHECK(categoria IN ('Mão de Obra','Insumos','Equipamentos')) NOT NULL,
            descricao   TEXT NOT NULL,
            valor       REAL NOT NULL,
            id_conta    INTEGER REFERENCES fin_conta(id),
            data_pagamento TEXT,
            status      TEXT CHECK(status IN ('Realizado','Previsto')) NOT NULL DEFAULT 'Realizado',
            id_lancamento INTEGER REFERENCES fin_lancamento(id),
            fornecedor  TEXT,
            observacao  TEXT
        )
    """)

    # Curva de crescimento padrão (clone eucalipto Cerrado — ajustável)
    if conn.execute("SELECT COUNT(*) FROM eu_curva_crescimento").fetchone()[0] == 0:
        curva_padrao = [
            (12, 20), (24, 55), (36, 95), (48, 135),
            (60, 170), (72, 200), (84, 225), (96, 245),
        ]
        conn.executemany(
            "INSERT INTO eu_curva_crescimento (idade_meses, volume_m3_ha) VALUES (?,?)",
            curva_padrao
        )

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# HELPERS FINANCEIROS
# ─────────────────────────────────────────────
def criar_lancamento(conn, tipo, valor, descricao, categoria,
                     id_conta=None, data=None, data_pagamento=None,
                     status="Previsto", origem=None, id_origem=None,
                     beneficiario=None):
    """Cria um lançamento financeiro e retorna o id."""
    cur = conn.execute("""
        INSERT INTO fin_lancamento
            (data, data_pagamento, tipo, valor, descricao, beneficiario,
             categoria, id_conta, status, origem, id_origem)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (data or date.today().isoformat(), data_pagamento,
          tipo, valor, descricao, beneficiario,
          categoria, id_conta, status, origem, id_origem))
    return cur.lastrowid

def inventario_talhao(conn, id_talhao, data_ref=None):
    """Calcula volume m³ estimado para um talhão na data_ref."""
    talhao = conn.execute(
        "SELECT area_ha, data_plantio FROM eu_talhao WHERE id=?", (id_talhao,)
    ).fetchone()
    if not talhao or not talhao["data_plantio"]:
        return None
    data_ref = data_ref or date.today().isoformat()
    try:
        dt_plantio = datetime.fromisoformat(talhao["data_plantio"])
        dt_ref     = datetime.fromisoformat(data_ref)
        meses = (dt_ref.year - dt_plantio.year) * 12 + (dt_ref.month - dt_plantio.month)
    except Exception:
        return None
    if meses <= 0:
        return 0.0
    curva = conn.execute(
        "SELECT idade_meses, volume_m3_ha FROM eu_curva_crescimento ORDER BY idade_meses"
    ).fetchall()
    if not curva:
        return None
    # Interpola linearmente
    pts = [(r["idade_meses"], r["volume_m3_ha"]) for r in curva]
    if meses <= pts[0][0]:
        vol_ha = pts[0][1] * (meses / pts[0][0])
    elif meses >= pts[-1][0]:
        vol_ha = pts[-1][1]
    else:
        for i in range(len(pts) - 1):
            if pts[i][0] <= meses <= pts[i+1][0]:
                t = (meses - pts[i][0]) / (pts[i+1][0] - pts[i][0])
                vol_ha = pts[i][1] + t * (pts[i+1][1] - pts[i][1])
                break
        else:
            vol_ha = pts[-1][1]
    return round(vol_ha * talhao["area_ha"], 1)

# ─────────────────────────────────────────────
# COMPONENTES TUI
# ─────────────────────────────────────────────
class Colors:
    def init(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE,   -1)                   # normal
        curses.init_pair(2, curses.COLOR_BLACK,   curses.COLOR_WHITE)   # selecionado: preto no branco
        curses.init_pair(3, curses.COLOR_YELLOW,  -1)                   # título
        curses.init_pair(4, curses.COLOR_GREEN,   -1)                   # sucesso
        curses.init_pair(5, curses.COLOR_RED,     -1)                   # erro
        curses.init_pair(6, curses.COLOR_CYAN,    -1)                   # info
        curses.init_pair(7, curses.COLOR_BLACK,   curses.COLOR_CYAN)    # header
        curses.init_pair(8, curses.COLOR_CYAN,    -1)                   # linha alternada
        curses.init_pair(9, curses.COLOR_YELLOW,  -1)                   # aviso

C = Colors()
NORMAL   = lambda: curses.color_pair(1)
SEL      = lambda: curses.color_pair(2)                  # preto sobre cinza, sem bold
SEL_BTN  = lambda: curses.color_pair(4) | curses.A_BOLD | curses.A_REVERSE
TITLE    = lambda: curses.color_pair(3) | curses.A_BOLD
SUCCESS  = lambda: curses.color_pair(4) | curses.A_BOLD
ERROR    = lambda: curses.color_pair(5) | curses.A_BOLD
INFO     = lambda: curses.color_pair(6)
HEADER   = lambda: curses.color_pair(7)                  # preto puro sobre azul, sem bold
ALTROW   = lambda: curses.color_pair(8)
WARN     = lambda: curses.color_pair(9)

def safe_addstr(win, y, x, text, attr=None):
    h, w = win.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    text = str(text)
    max_len = w - x - 1
    if max_len <= 0:
        return
    text = text[:max_len]
    try:
        if attr is not None:
            win.addstr(y, x, text, attr)
        else:
            win.addstr(y, x, text)
    except curses.error:
        pass

def draw_box(win, title=""):
    try:
        win.box()
    except curses.error:
        pass
    if title:
        h, w = win.getmaxyx()
        t = f" {title} "
        x = max(2, (w - len(t)) // 2)
        safe_addstr(win, 0, x, t, TITLE())

def draw_header(stdscr, title="🐄  GADO — Gestão de Fazenda"):
    h, w = stdscr.getmaxyx()
    stdscr.attron(HEADER())
    stdscr.addstr(0, 0, " " * w)
    safe_addstr(stdscr, 0, 2, title)
    today = date.today().strftime("%d/%m/%Y")
    safe_addstr(stdscr, 0, w - len(today) - 2, today)
    stdscr.attroff(HEADER())

def draw_footer(stdscr, hints="↑↓ Navegar  Enter Selecionar  Q Sair"):
    h, w = stdscr.getmaxyx()
    stdscr.attron(HEADER())
    stdscr.addstr(h - 1, 0, " " * (w - 1))
    safe_addstr(stdscr, h - 1, 2, hints)
    stdscr.attroff(HEADER())

# ─────────────────────────────────────────────
# MENU NAVEGÁVEL
# ─────────────────────────────────────────────
def menu(stdscr, items, title="", y_off=2, x_off=2, width=30):
    """Exibe menu navegável. Retorna índice selecionado ou -1 para voltar."""
    current = 0
    h, w = stdscr.getmaxyx()
    height = len(items) + 4

    win = curses.newwin(height, width, y_off, x_off)

    while True:
        win.erase()
        draw_box(win, title)
        for i, item in enumerate(items):
            icon, label = item if isinstance(item, tuple) else ("", item)
            text = f"  {icon} {label}" if icon else f"  {label}"
            attr = SEL() if i == current else NORMAL()
            safe_addstr(win, i + 2, 1, text.ljust(width - 2), attr)
        win.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            current = (current - 1) % len(items)
        elif key in (curses.KEY_DOWN, ord('j')):
            current = (current + 1) % len(items)
        elif key in (curses.KEY_ENTER, 10, 13):
            return current
        elif key in (ord('q'), ord('Q'), 27):
            return -1

# ─────────────────────────────────────────────
# FORMULÁRIO GENÉRICO
# ─────────────────────────────────────────────
def form(stdscr, fields, title="", y_off=2, x_off=2, width=60):
    """
    fields: lista de dicts com keys: label, default, required, options, type
    Retorna dict com valores ou None se cancelado.
    current pode ser 0..len(fields)-1 (campos) ou len(fields) (SALVAR) ou len(fields)+1 (CANCELAR)
    """
    h, w = stdscr.getmaxyx()
    # Ajusta posição para caber na tela
    max_h = h - 2
    field_h = 3
    buttons_h = 3
    header_h = 3
    max_fields_visible = (max_h - header_h - buttons_h) // field_h
    width = min(width, w - x_off - 2)
    height = min(len(fields) * field_h + header_h + buttons_h, max_h)
    y_off = max(1, min(y_off, h - height - 1))

    values = {f["label"]: f.get("default", "") for f in fields}
    # current: 0..N-1 = campos, N = SALVAR, N+1 = CANCELAR
    N = len(fields)
    current = 0
    scroll = 0  # primeiro campo visível

    while True:
        win = curses.newwin(height, width, y_off, x_off)
        win.erase()
        draw_box(win, title)
        safe_addstr(win, 1, 2, "↑↓/Tab navegar  Enter editar/salvar  Esc cancelar", INFO())

        # Número de campos visíveis na janela
        visible_area = height - header_h - buttons_h
        visible_count = visible_area // field_h

        # Ajusta scroll para manter current visível (só para campos)
        if current < N:
            if current < scroll:
                scroll = current
            elif current >= scroll + visible_count:
                scroll = current - visible_count + 1

        # Desenha campos visíveis
        for slot in range(visible_count):
            fi = slot + scroll
            if fi >= N:
                break
            field = fields[fi]
            wy = slot * field_h + header_h
            label = field["label"]
            required = field.get("required", False)
            val = values[label]
            req_mark = "*" if required else " "
            is_cur = (fi == current)

            safe_addstr(win, wy, 2, f"{req_mark} {label}:", TITLE() if is_cur else WARN())

            options = field.get("options")
            display = val if val else ("—" if not options else f"[escolher]")
            field_attr = SEL() if is_cur else ALTROW()
            safe_addstr(win, wy + 1, 4, f"  {display:<{width-8}}  ", field_attr)

        # Botões sempre no final
        btn_y = height - 2
        salvar_attr  = SEL_BTN() if current == N     else SUCCESS()
        cancel_attr  = SEL_BTN() if current == N + 1 else ERROR()
        safe_addstr(win, btn_y, 3,  "[ SALVAR ]",   salvar_attr)
        safe_addstr(win, btn_y, 15, "[ CANCELAR ]", cancel_attr)

        # Indicador de scroll
        if N > visible_count:
            if scroll > 0:
                safe_addstr(win, header_h, width - 3, "↑", INFO())
            if scroll + visible_count < N:
                safe_addstr(win, height - 3, width - 3, "↓", INFO())

        win.refresh()
        key = stdscr.getch()

        if key == 27:  # ESC = cancelar
            return None

        elif key in (curses.KEY_DOWN, 9):  # Tab ou seta baixo
            current = (current + 1) % (N + 2)

        elif key == curses.KEY_UP:
            current = (current - 1) % (N + 2)

        elif key in (curses.KEY_ENTER, 10, 13):
            if current == N:  # SALVAR
                missing = [f["label"] for f in fields if f.get("required") and not str(values[f["label"]]).strip()]
                if missing:
                    flash(stdscr, f"Obrigatório: {', '.join(missing)}", error=True)
                    current = next(i for i, f in enumerate(fields) if f["label"] == missing[0])
                    continue
                return values

            elif current == N + 1:  # CANCELAR
                return None

            else:  # Editar campo atual
                field = fields[current]
                options = field.get("options")
                if options:
                    opts = [str(o) for o in options]
                    cur_idx = opts.index(values[field["label"]]) if values[field["label"]] in opts else 0
                    # Calcula posição do picker na tela
                    slot = current - scroll
                    picker_y = max(1, min(y_off + slot * field_h + header_h + 1, h - len(opts) - 4))
                    chosen = option_picker(stdscr, opts, field["label"], picker_y, x_off + 4, initial_pos=cur_idx)
                    if chosen is not None:
                        values[field["label"]] = opts[chosen]
                else:
                    slot = current - scroll
                    wy = slot * field_h + header_h
                    val = text_input(win, wy + 1, 6, width - 10, values[field["label"]])
                    values[field["label"]] = val
                # Avança para próximo campo automaticamente
                if current < N - 1:
                    current += 1

    return None

def option_picker(stdscr, options, title="", y=5, x=10, initial_pos=0):
    """Mini menu para escolher uma opção. Começa no item initial_pos."""
    width = max(len(o) for o in options) + 6
    width = max(width, len(title) + 4)
    height = len(options) + 4
    h, w = stdscr.getmaxyx()
    y = min(y, h - height - 1)
    x = min(x, w - width - 1)

    win = curses.newwin(height, width, max(0, y), max(0, x))
    current = max(0, min(initial_pos, len(options) - 1))
    while True:
        win.erase()
        draw_box(win, title)
        for i, opt in enumerate(options):
            attr = SEL() if i == current else NORMAL()
            safe_addstr(win, i + 2, 2, f" {opt} ".ljust(width - 3), attr)
        win.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP:
            current = (current - 1) % len(options)
        elif key == curses.KEY_DOWN:
            current = (current + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return current
        elif key in (27, ord('q')):
            return None

def text_input(win, y, x, width, initial=""):
    """Campo de edição de texto inline."""
    curses.curs_set(1)
    text = list(initial)
    pos = len(text)
    h, w = win.getmaxyx()

    while True:
        display = "".join(text)
        safe_addstr(win, y, x, f"{display:<{width}}", SEL())
        try:
            win.move(y, x + min(pos, width - 1))
        except curses.error:
            pass
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_ENTER, 10, 13, 9):  # Enter ou Tab confirma
            break
        elif key == 27:  # ESC cancela
            curses.curs_set(0)
            return initial
        elif key == curses.KEY_BACKSPACE or key == 127:
            if pos > 0:
                text.pop(pos - 1)
                pos -= 1
        elif key == curses.KEY_LEFT:
            pos = max(0, pos - 1)
        elif key == curses.KEY_RIGHT:
            pos = min(len(text), pos + 1)
        elif key == curses.KEY_HOME:
            pos = 0
        elif key == curses.KEY_END:
            pos = len(text)
        elif 32 <= key <= 126:
            text.insert(pos, chr(key))
            pos += 1

    curses.curs_set(0)
    return "".join(text).strip()

def flash(stdscr, msg, error=False):
    """Exibe mensagem temporária na parte inferior."""
    h, w = stdscr.getmaxyx()
    attr = ERROR() if error else SUCCESS()
    safe_addstr(stdscr, h - 2, 2, f" {msg} ".ljust(w - 4), attr)
    stdscr.refresh()
    curses.napms(1800)

def confirm(stdscr, msg, y=10, x=10):
    """Caixa de confirmação Sim/Não."""
    width = max(len(msg) + 6, 30)
    win = curses.newwin(6, width, y, x)
    current = 0
    while True:
        win.erase()
        draw_box(win, "Confirmar")
        safe_addstr(win, 2, 2, msg, WARN())
        sim_attr = SEL() if current == 0 else NORMAL()
        nao_attr = SEL() if current == 1 else NORMAL()
        safe_addstr(win, 4, 4, "  Sim  ", sim_attr)
        safe_addstr(win, 4, 14, "  Não  ", nao_attr)
        win.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            current = 1 - current
        elif key in (curses.KEY_ENTER, 10, 13):
            return current == 0
        elif key in (27, ord('n'), ord('N')):
            return False
        elif key in (ord('s'), ord('S')):
            return True

# ─────────────────────────────────────────────
# TABELA NAVEGÁVEL
# ─────────────────────────────────────────────
def table_view(stdscr, rows, columns, title="", col_widths=None, footer=None):
    """Exibe tabela navegável. Retorna índice da linha selecionada ou -1.
    Suporta footer customizado e hotkeys especiais:
      -99 = N (nova), -98 = R (romaneio), -97 = P (recebimento)
    """
    if not rows:
        flash(stdscr, "Nenhum registro encontrado.")
        return -1

    h, w = stdscr.getmaxyx()
    if not col_widths:
        col_widths = [max(len(str(c)), max(len(str(r[i])) for r in rows))
                      for i, c in enumerate(columns)]
    total_w = sum(col_widths) + len(col_widths) * 2 + 3
    total_w = min(total_w, w - 2)

    win_h = h - 4
    win = curses.newwin(win_h, total_w, 2, 1)

    current = 0
    offset = 0
    visible = win_h - 4  # linhas visíveis

    while True:
        win.erase()
        draw_box(win, title)

        # Header
        x = 2
        for i, col in enumerate(columns):
            cw = col_widths[i] if i < len(col_widths) else 10
            safe_addstr(win, 1, x, str(col)[:cw].ljust(cw), HEADER())
            x += cw + 2

        # Linhas
        for idx in range(visible):
            row_idx = idx + offset
            if row_idx >= len(rows):
                break
            row = rows[row_idx]
            x = 2
            is_sel = row_idx == current
            is_alt = row_idx % 2 == 0
            base_attr = SEL() if is_sel else (ALTROW() if is_alt else NORMAL())

            for i, col in enumerate(columns):
                cw = col_widths[i] if i < len(col_widths) else 10
                val = str(row[i]) if row[i] is not None else "—"
                safe_addstr(win, idx + 2, x, val[:cw].ljust(cw), base_attr)
                x += cw + 2

        # Footer
        footer_text = footer if footer else f"Linha {current+1}/{len(rows)}  ↑↓ navegar  Enter selecionar  Q voltar"
        safe_addstr(win, win_h - 1, 2, footer_text[:total_w-4], INFO())
        win.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP:
            if current > 0:
                current -= 1
                if current < offset:
                    offset = current
        elif key == curses.KEY_DOWN:
            if current < len(rows) - 1:
                current += 1
                if current >= offset + visible:
                    offset = current - visible + 1
        elif key == curses.KEY_PPAGE:
            current = max(0, current - visible)
            offset = max(0, offset - visible)
        elif key == curses.KEY_NPAGE:
            current = min(len(rows) - 1, current + visible)
            offset = min(max(0, len(rows) - visible), offset + visible)
        elif key in (curses.KEY_ENTER, 10, 13):
            return current
        elif key in (ord('n'), ord('N')):
            return -99
        elif key in (ord('r'), ord('R')):
            return -98
        elif key in (ord('p'), ord('P')):
            return -97
        elif key in (ord('q'), ord('Q'), 27):
            return -1

# ─────────────────────────────────────────────
# TELAS DE DETALHE
# ─────────────────────────────────────────────
def detail_view(stdscr, pairs, title=""):
    """Exibe pares chave-valor com scroll. Q ou Enter para sair."""
    h, w = stdscr.getmaxyx()
    wh = h - 4
    ww = w - 4
    win = curses.newwin(wh, ww, 2, 2)

    # Filtra pares com valor
    # Mantém pares com valor, seções (label "──...") e linhas indentadas ("  ")
    visible_pairs = [(l, v) for l, v in pairs if v is not None and (l.startswith("──") or l == "  " or str(v) not in ("", "None"))]
    col_label = max((len(l) for l, _ in visible_pairs), default=10) + 2
    col_val   = ww - col_label - 5

    total = len(visible_pairs)
    scroll = 0
    content_h = wh - 4  # linhas úteis (exceto box + header + footer)

    while True:
        win.erase()
        draw_box(win, title)
        safe_addstr(win, 1, 2, "↑↓ rolar  Q/Enter voltar", INFO())

        for i in range(content_h):
            idx = i + scroll
            if idx >= total:
                break
            label, val = visible_pairs[idx]
            wy = i + 2
            # Linha de seção (label começa com ──)
            if label.startswith("──") or label == "  ":
                if label == "  ":
                    # linha de dados indentada
                    safe_addstr(win, wy, 4, str(val)[:ww-6], NORMAL())
                else:
                    # cabeçalho de seção
                    section = f" {label} "
                    if val:
                        section += f"({val})"
                    safe_addstr(win, wy, 2, section[:ww-4], TITLE())
            else:
                safe_addstr(win, wy, 2, f"{label}:".ljust(col_label), WARN())
                safe_addstr(win, wy, 2 + col_label, str(val)[:col_val], NORMAL())

        # Indicadores de scroll
        if scroll > 0:
            safe_addstr(win, 2, ww - 3, " ↑ ", INFO())
        if scroll + content_h < total:
            safe_addstr(win, wh - 2, ww - 3, " ↓ ", INFO())
            safe_addstr(win, wh - 1, 2, f"Linha {scroll+1}-{min(scroll+content_h, total)}/{total}", INFO())

        win.refresh()
        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27, curses.KEY_ENTER, 10, 13):
            break
        elif key == curses.KEY_UP:
            scroll = max(0, scroll - 1)
        elif key == curses.KEY_DOWN:
            scroll = min(max(0, total - content_h), scroll + 1)
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - content_h)
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0, total - content_h), scroll + content_h)

# ─────────────────────────────────────────────
# TELAS DE MÓDULOS
# ─────────────────────────────────────────────

# ── ANIMAIS ─────────────────────────────────
def screen_animais(stdscr):
    while True:
        idx = menu(stdscr, [
            ("🐄", "Listar Animais"),
            ("🔍", "Buscar por Brinco"),
            ("✏️ ", "Editar Animal"),
            ("🗑️ ", "Deletar Animal"),
            ("⬅️ ", "Voltar"),
        ], title=" Animais ", y_off=3, x_off=4, width=36)

        if idx == 0: listar_animais(stdscr)
        elif idx == 1: buscar_animal(stdscr)
        elif idx == 2: editar_animal(stdscr)
        elif idx == 3: deletar_animal(stdscr)
        elif idx in (-1, 4): break

def listar_animais(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT a.brinco, a.nome, a.sexo, a.categoria, a.raca,
               a.status, a.origem, a.data_nascimento
        FROM animal a ORDER BY a.brinco
    """).fetchall()
    conn.close()
    data = [[r["brinco"], r["nome"] or "—", r["sexo"], r["categoria"],
             r["raca"] or "—", r["status"], r["origem"]] for r in rows]
    idx = table_view(stdscr, data,
                     ["Brinco","Nome","Sx","Categoria","Raça","Status","Origem"],
                     title=" Animais ",
                     col_widths=[8,12,3,10,10,10,8])
    if idx >= 0:
        ver_animal(stdscr, rows[idx]["brinco"])

def ver_animal(stdscr, brinco):
    conn = get_db()
    a = conn.execute("""
        SELECT a.*, m.brinco as brinco_mae, p.brinco as brinco_pai
        FROM animal a
        LEFT JOIN animal m ON a.id_mae=m.id
        LEFT JOIN animal p ON a.id_pai=p.id
        WHERE a.brinco=?
    """, (brinco,)).fetchone()
    if not a:
        conn.close()
        flash(stdscr, f"Animal {brinco} não encontrado.", error=True)
        return

    # Lote atual
    lote_atual = conn.execute("""
        SELECT l.nome, l.fase, p.nome as pasto
        FROM animal_lote al
        JOIN lote l ON al.id_lote=l.id
        LEFT JOIN pasto p ON l.id_pasto=p.id
        WHERE al.id_animal=? AND al.data_saida IS NULL
    """, (a["id"],)).fetchone()

    # Pesagens (todas, do mais recente ao mais antigo)
    pesagens = conn.execute("""
        SELECT data_pesagem, peso_kg, fase FROM pesagem
        WHERE id_animal=? ORDER BY data_pesagem DESC
    """, (a["id"],)).fetchall()

    # Calcular GMD entre pesagens consecutivas
    pesagens_list = list(pesagens)
    pesos_fmt = []
    for i, p in enumerate(pesagens_list):
        gmd_str = ""
        if i < len(pesagens_list) - 1:
            p_ant = pesagens_list[i + 1]
            try:
                dias = (datetime.fromisoformat(p["data_pesagem"]) -
                        datetime.fromisoformat(p_ant["data_pesagem"])).days
                if dias > 0:
                    gmd = (p["peso_kg"] - p_ant["peso_kg"]) / dias
                    gmd_str = f"  GMD {gmd:+.3f} kg/d"
            except Exception:
                pass
        fase_str = f" [{p['fase']}]" if p["fase"] else ""
        pesos_fmt.append(f"{p['data_pesagem']}  {p['peso_kg']} kg{fase_str}{gmd_str}")

    # Reproduções (fêmea)
    repros = conn.execute("""
        SELECT r.tipo, r.data_cobertura, r.resultado_dg,
               r.data_parto_previsto, r.data_parto_real,
               t.brinco as touro, c.brinco as cria
        FROM reproducao r
        LEFT JOIN animal t ON r.id_touro=t.id
        LEFT JOIN animal c ON r.id_cria=c.id
        WHERE r.id_femea=? ORDER BY r.data_cobertura DESC
    """, (a["id"],)).fetchall()

    # Crias (se for mãe)
    crias = conn.execute("""
        SELECT brinco, categoria, data_nascimento, status
        FROM animal WHERE id_mae=? ORDER BY data_nascimento DESC
    """, (a["id"],)).fetchall()

    # Sanidade (últimas 10)
    sanidades = conn.execute("""
        SELECT data, tipo, produto, dose_ml, responsavel FROM sanidade
        WHERE id_animal=? ORDER BY data DESC LIMIT 10
    """, (a["id"],)).fetchall()

    # Movimentações
    movs = conn.execute("""
        SELECT tipo, data, peso_kg, valor_arroba, valor_total, contraparte, nota_fiscal
        FROM movimentacao WHERE id_animal=? ORDER BY data DESC
    """, (a["id"],)).fetchall()

    conn.close()

    pairs = []

    # ── Identificação ──
    pairs.append(("── IDENTIFICAÇÃO ──", ""))
    pairs.append(("Brinco",         a["brinco"]))
    pairs.append(("SISBOV",         a["sisbov"]))
    pairs.append(("Nome / Apelido", a["nome"]))

    # ── Dados zootécnicos ──
    pairs.append(("── DADOS ZOOTÉCNICOS ──", ""))
    pairs.append(("Sexo",           "Fêmea" if a["sexo"] == "F" else "Macho"))
    pairs.append(("Categoria",      a["categoria"]))
    pairs.append(("Raça",           a["raca"]))
    pairs.append(("Nascimento",     a["data_nascimento"]))
    pairs.append(("Peso Nasc.",     f"{a['peso_nascimento']} kg" if a["peso_nascimento"] else None))

    # ── Genealogia ──
    pairs.append(("── GENEALOGIA ──", ""))
    pairs.append(("Mãe (brinco)",   a["brinco_mae"]))
    pairs.append(("Pai (brinco)",   a["brinco_pai"]))

    # ── Origem e status ──
    pairs.append(("── ORIGEM E STATUS ──", ""))
    pairs.append(("Origem",         a["origem"]))
    pairs.append(("Fazenda Origem", a["fazenda_origem"]))
    pairs.append(("Status",         a["status"]))
    pairs.append(("Data Entrada",   a["data_entrada"]))
    pairs.append(("Data Saída",     a["data_saida"]))
    pairs.append(("Observação",     a["observacao"]))

    # ── Lote atual ──
    pairs.append(("── LOTE ATUAL ──", ""))
    if lote_atual:
        pairs.append(("Lote",   lote_atual["nome"]))
        pairs.append(("Fase",   lote_atual["fase"]))
        pairs.append(("Pasto",  lote_atual["pasto"]))
    else:
        pairs.append(("Lote",   "Sem lote atribuído"))

    # ── Pesagens ──
    pairs.append(("── PESAGENS ──", f"{len(pesagens_list)} registros"))
    for p in pesos_fmt:
        pairs.append(("  ", p))

    # ── Reprodução ──
    if a["sexo"] == "F":
        pairs.append(("── REPRODUÇÃO ──", f"{len(repros)} coberturas"))
        for r in repros:
            dg = r["resultado_dg"] or "DG pendente"
            touro = f"Touro: {r['touro']}" if r["touro"] else "Touro: —"
            linha = f"{r['data_cobertura']} {r['tipo']}  {touro}  DG: {dg}"
            if r["data_parto_real"]:
                linha += f"  Parto: {r['data_parto_real']}"
                if r["cria"]:
                    linha += f" (cria: {r['cria']})"
            elif r["data_parto_previsto"]:
                linha += f"  Prev.: {r['data_parto_previsto']}"
            pairs.append(("  ", linha))

    # ── Crias ──
    if crias:
        pairs.append(("── CRIAS ──", f"{len(crias)} filhos"))
        for c in crias:
            nasc = c["data_nascimento"] or "—"
            pairs.append(("  ", f"{c['brinco']}  {c['categoria']}  {nasc}  [{c['status']}]"))

    # ── Sanidade ──
    if sanidades:
        pairs.append(("── SANIDADE ──", f"últimos {len(sanidades)} registros"))
        for s in sanidades:
            dose = f" {s['dose_ml']} ml" if s["dose_ml"] else ""
            resp = f" | {s['responsavel']}" if s["responsavel"] else ""
            pairs.append(("  ", f"{s['data']}  {s['tipo']}  {s['produto'] or '—'}{dose}{resp}"))

    # ── Movimentações ──
    if movs:
        pairs.append(("── MOVIMENTAÇÕES ──", f"{len(movs)} registros"))
        for m in movs:
            val = f"R$ {m['valor_total']:.2f}" if m["valor_total"] else "—"
            peso = f"{m['peso_kg']} kg" if m["peso_kg"] else "—"
            arr  = f"@ R$ {m['valor_arroba']:.2f}" if m["valor_arroba"] else ""
            cp   = f" | {m['contraparte']}" if m["contraparte"] else ""
            pairs.append(("  ", f"{m['data']}  {m['tipo']}  {peso} {arr}  {val}{cp}"))

    detail_view(stdscr, pairs, title=f" Animal: {brinco} ")

def cadastrar_animal(stdscr):
    fields = [
        {"label": "Brinco",      "required": True},
        {"label": "Sexo",        "required": True,  "options": ["M","F"]},
        {"label": "Categoria",   "required": True,  "options": ["Bezerro","Bezerra","Novilho","Novilha","Vaca","Touro","Boi"]},
        {"label": "Raça",        "default": ""},
        {"label": "Nome"},
        {"label": "Nascimento",  "default": "", "placeholder": "AAAA-MM-DD"},
        {"label": "Peso Nasc.",  "default": ""},
        {"label": "Brinco Mãe",  "default": ""},
        {"label": "Brinco Pai",  "default": ""},
        {"label": "Origem",      "options": ["Nascido","Comprado"], "default": "Nascido"},
        {"label": "Fazenda Orig."},
        {"label": "Observação"},
    ]
    result = form(stdscr, fields, title=" Novo Animal ", width=55)
    if result is None:
        return
    conn = get_db()
    try:
        id_mae = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco Mãe"],)).fetchone()
        id_pai = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco Pai"],)).fetchone()
        peso = float(result["Peso Nasc."]) if result["Peso Nasc."] else None
        conn.execute("""INSERT INTO animal
            (brinco,sexo,categoria,raca,nome,data_nascimento,peso_nascimento,
             id_mae,id_pai,origem,fazenda_origem,observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (result["Brinco"], result["Sexo"], result["Categoria"],
             result["Raça"] or None, result["Nome"] or None,
             result["Nascimento"] or None, peso,
             id_mae["id"] if id_mae else None,
             id_pai["id"] if id_pai else None,
             result["Origem"] or "Nascido",
             result["Fazenda Orig."] or None,
             result["Observação"] or None))
        conn.commit()
        flash(stdscr, f"Animal {result['Brinco']} cadastrado com sucesso!")
    except sqlite3.IntegrityError:
        flash(stdscr, f"Brinco {result['Brinco']} já existe!", error=True)
    finally:
        conn.close()

def buscar_animal(stdscr):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 40, h//2 - 2, w//2 - 20)
    win.erase()
    draw_box(win, " Buscar Animal ")
    safe_addstr(win, 2, 2, "Brinco: ", TITLE())
    win.refresh()
    brinco = text_input(win, 2, 10, 26)
    if brinco:
        ver_animal(stdscr, brinco)

def editar_animal(stdscr):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 40, h//2 - 2, w//2 - 20)
    win.erase()
    draw_box(win, " Editar Animal ")
    safe_addstr(win, 2, 2, "Brinco: ", TITLE())
    win.refresh()
    brinco = text_input(win, 2, 10, 26)
    if not brinco:
        return
    conn = get_db()
    a = conn.execute("SELECT * FROM animal WHERE brinco=?", (brinco,)).fetchone()
    conn.close()
    if not a:
        flash(stdscr, f"Animal {brinco} não encontrado.", error=True)
        return
    fields = [
        {"label": "Brinco",     "default": a["brinco"],           "required": True},
        {"label": "Categoria",  "default": a["categoria"],        "options": ["Bezerro","Bezerra","Novilho","Novilha","Vaca","Touro","Boi"]},
        {"label": "Nome",       "default": a["nome"] or ""},
        {"label": "Raça",       "default": a["raca"] or ""},
        {"label": "Status",     "default": a["status"],           "options": ["Ativo","Vendido","Morto","Descartado"]},
        {"label": "Origem",     "default": a["origem"],           "options": ["Nascido","Comprado"]},
        {"label": "Faz. Orig.", "default": a["fazenda_origem"] or ""},
        {"label": "SISBOV",     "default": a["sisbov"] or ""},
        {"label": "Obs.",       "default": a["observacao"] or ""},
    ]
    result = form(stdscr, fields, title=f" Editar {brinco} ", width=55)
    if result is None:
        return
    conn = get_db()
    conn.execute("""UPDATE animal SET brinco=?,categoria=?,nome=?,raca=?,
        status=?,origem=?,fazenda_origem=?,sisbov=?,observacao=? WHERE brinco=?""",
        (result["Brinco"], result["Categoria"], result["Nome"] or None,
         result["Raça"] or None, result["Status"], result["Origem"],
         result["Faz. Orig."] or None, result["SISBOV"] or None,
         result["Obs."] or None, brinco))
    conn.commit()
    conn.close()
    flash(stdscr, f"Animal {brinco} atualizado!")

def deletar_animal(stdscr):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 40, h//2 - 2, w//2 - 20)
    win.erase()
    draw_box(win, " Deletar Animal ")
    safe_addstr(win, 2, 2, "Brinco: ", TITLE())
    win.refresh()
    brinco = text_input(win, 2, 10, 26)
    if not brinco:
        return
    conn = get_db()
    a = conn.execute("SELECT id FROM animal WHERE brinco=?", (brinco,)).fetchone()
    if not a:
        conn.close()
        flash(stdscr, f"Animal {brinco} não encontrado.", error=True)
        return
    aid = a["id"]
    deps = {
        "pesagens":    conn.execute("SELECT COUNT(*) FROM pesagem WHERE id_animal=?", (aid,)).fetchone()[0],
        "movimentações": conn.execute("SELECT COUNT(*) FROM movimentacao WHERE id_animal=?", (aid,)).fetchone()[0],
        "reproduções": conn.execute("SELECT COUNT(*) FROM reproducao WHERE id_femea=? OR id_touro=? OR id_cria=?", (aid,aid,aid)).fetchone()[0],
    }
    conn.close()
    tem_deps = any(v > 0 for v in deps.items() if isinstance(v, int))
    msg = f"Deletar {brinco}? Isso é irreversível!"
    if not confirm(stdscr, msg, h//2, w//2 - 20):
        return
    conn = get_db()
    conn.execute("DELETE FROM pesagem WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM movimentacao WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM sanidade WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM reproducao WHERE id_femea=? OR id_touro=? OR id_cria=?", (aid,aid,aid))
    conn.execute("DELETE FROM mortalidade WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM animal_lote WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM animal WHERE id=?", (aid,))
    conn.commit()
    conn.close()
    flash(stdscr, f"Animal {brinco} deletado.")

# ── PESAGEM ─────────────────────────────────
def screen_pesagem(stdscr):
    while True:
        idx = menu(stdscr, [
            ("⚖️ ", "Registrar Pesagem"),
            ("📋", "Histórico de Pesagens"),
            ("⬅️ ", "Voltar"),
        ], title=" Pesagem ", y_off=3, x_off=4, width=34)
        if idx == 0: registrar_pesagem(stdscr)
        elif idx == 1: historico_pesagem(stdscr)
        elif idx in (-1, 2): break

def registrar_pesagem(stdscr):
    fields = [
        {"label": "Brinco",  "required": True},
        {"label": "Peso kg", "required": True},
        {"label": "Fase",    "options": ["","Cria","Recria","Engorda"], "default": ""},
        {"label": "Data",    "default": date.today().isoformat()},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nova Pesagem ", width=50)
    if result is None:
        return
    conn = get_db()
    a = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco"],)).fetchone()
    if not a:
        conn.close()
        flash(stdscr, f"Animal {result['Brinco']} não encontrado.", error=True)
        return
    try:
        peso = float(result["Peso kg"])
        data = result["Data"] or date.today().isoformat()

        # Calcula GMD
        ant = conn.execute("""SELECT peso_kg, data_pesagem FROM pesagem
            WHERE id_animal=? AND data_pesagem < ? ORDER BY data_pesagem DESC LIMIT 1""",
            (a["id"], data)).fetchone()

        conn.execute("INSERT INTO pesagem (id_animal,data_pesagem,peso_kg,fase,observacao) VALUES (?,?,?,?,?)",
                     (a["id"], data, peso, result["Fase"] or None, result["Obs."] or None))
        # Recalcula valor/@ de compra se o animal foi comprado sem peso
        _recalcular_arroba_compra(conn, a["id"])
        conn.commit()

        msg = f"Pesagem {peso} kg registrada para {result['Brinco']}"
        if ant:
            dias = (datetime.fromisoformat(data) - datetime.fromisoformat(ant["data_pesagem"])).days
            if dias > 0:
                gmd = (peso - ant["peso_kg"]) / dias
                msg += f"  |  GMD: {gmd:.3f} kg/dia"
        flash(stdscr, msg)
    except ValueError:
        flash(stdscr, "Peso inválido.", error=True)
    finally:
        conn.close()

def historico_pesagem(stdscr):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 40, h//2 - 2, w//2 - 20)
    win.erase()
    draw_box(win, " Histórico ")
    safe_addstr(win, 2, 2, "Brinco: ", TITLE())
    win.refresh()
    brinco = text_input(win, 2, 10, 26)
    if not brinco:
        return
    conn = get_db()
    a = conn.execute("SELECT id FROM animal WHERE brinco=?", (brinco,)).fetchone()
    if not a:
        conn.close()
        flash(stdscr, f"Animal {brinco} não encontrado.", error=True)
        return
    rows = conn.execute("""SELECT data_pesagem, peso_kg, fase FROM pesagem
        WHERE id_animal=? ORDER BY data_pesagem""", (a["id"],)).fetchall()
    conn.close()
    data = []
    for i, r in enumerate(rows):
        gmd = "—"
        if i > 0:
            dias = (datetime.fromisoformat(r["data_pesagem"]) -
                    datetime.fromisoformat(rows[i-1]["data_pesagem"])).days
            if dias > 0:
                gmd = f"{(r['peso_kg']-rows[i-1]['peso_kg'])/dias:.3f}"
        data.append([r["data_pesagem"], r["peso_kg"], r["fase"] or "—", gmd])
    table_view(stdscr, data, ["Data","Peso (kg)","Fase","GMD"],
               title=f" Pesagens: {brinco} ", col_widths=[12,10,8,10])

# ── LOTES ────────────────────────────────────
def screen_lotes(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📦", "Listar Lotes"),
            ("➕", "Criar Lote"),
            ("🐄", "Ver Animais do Lote"),
            ("➡️ ", "Mover Animal p/ Lote"),
            ("⬅️ ", "Voltar"),
        ], title=" Lotes ", y_off=3, x_off=4, width=34)
        if idx == 0: listar_lotes(stdscr)
        elif idx == 1: criar_lote(stdscr)
        elif idx == 2: ver_lote(stdscr)
        elif idx == 3: mover_animal_lote(stdscr)
        elif idx in (-1, 4): break

def listar_lotes(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT l.nome, l.fase, p.nome as pasto, l.data_inicio,
               COUNT(al.id) as qtd
        FROM lote l
        LEFT JOIN pasto p ON l.id_pasto=p.id
        LEFT JOIN animal_lote al ON l.id=al.id_lote AND al.data_saida IS NULL
        GROUP BY l.id ORDER BY l.fase, l.nome
    """).fetchall()
    conn.close()
    data = [[r["nome"], r["fase"], r["pasto"] or "—", r["data_inicio"], r["qtd"]] for r in rows]
    table_view(stdscr, data, ["Nome","Fase","Pasto","Início","Animais"],
               title=" Lotes ", col_widths=[16,8,16,12,8])

def criar_lote(stdscr):
    conn = get_db()
    pastos = [r["nome"] for r in conn.execute("SELECT nome FROM pasto ORDER BY nome").fetchall()]
    conn.close()
    fields = [
        {"label": "Nome",  "required": True},
        {"label": "Fase",  "required": True, "options": ["Cria","Recria","Engorda"]},
        {"label": "Pasto", "options": [""]+pastos, "default": ""},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Novo Lote ", width=50)
    if result is None:
        return
    conn = get_db()
    try:
        id_pasto = conn.execute("SELECT id FROM pasto WHERE nome=?", (result["Pasto"],)).fetchone()
        conn.execute("INSERT INTO lote (nome,fase,id_pasto,observacao) VALUES (?,?,?,?)",
                     (result["Nome"], result["Fase"],
                      id_pasto["id"] if id_pasto else None,
                      result["Obs."] or None))
        conn.commit()
        flash(stdscr, f"Lote '{result['Nome']}' criado!")
    except sqlite3.IntegrityError:
        flash(stdscr, f"Lote '{result['Nome']}' já existe.", error=True)
    finally:
        conn.close()

def ver_lote(stdscr):
    conn = get_db()
    lotes = [r["nome"] for r in conn.execute("SELECT nome FROM lote ORDER BY nome").fetchall()]
    conn.close()
    if not lotes:
        flash(stdscr, "Nenhum lote cadastrado.", error=True)
        return
    idx = option_picker(stdscr, lotes, "Escolher Lote", 5, 10)
    if idx is None:
        return
    nome = lotes[idx]
    conn = get_db()
    lote = conn.execute("SELECT id FROM lote WHERE nome=?", (nome,)).fetchone()
    rows = conn.execute("""
        SELECT a.brinco, a.nome, a.sexo, a.categoria, al.data_entrada,
               (SELECT peso_kg FROM pesagem WHERE id_animal=a.id ORDER BY data_pesagem DESC LIMIT 1) as peso
        FROM animal_lote al JOIN animal a ON al.id_animal=a.id
        WHERE al.id_lote=? AND al.data_saida IS NULL ORDER BY a.brinco
    """, (lote["id"],)).fetchall()
    conn.close()
    data = [[r["brinco"], r["nome"] or "—", r["sexo"], r["categoria"],
             str(r["peso"])+" kg" if r["peso"] else "—", r["data_entrada"]] for r in rows]
    idx = table_view(stdscr, data, ["Brinco","Nome","Sx","Categoria","Último Peso","Entrada"],
                     title=f" Lote: {nome} ", col_widths=[8,12,3,10,12,12])
    if idx >= 0:
        ver_animal(stdscr, rows[idx]["brinco"])

def mover_animal_lote(stdscr):
    fields = [
        {"label": "Brinco", "required": True},
        {"label": "Lote",   "required": True},
    ]
    result = form(stdscr, fields, title=" Mover Animal ", width=50)
    if result is None:
        return
    conn = get_db()
    a = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco"],)).fetchone()
    l = conn.execute("SELECT id FROM lote WHERE nome=?", (result["Lote"],)).fetchone()
    if not a:
        conn.close(); flash(stdscr, "Animal não encontrado.", error=True); return
    if not l:
        conn.close(); flash(stdscr, "Lote não encontrado.", error=True); return
    conn.execute("UPDATE animal_lote SET data_saida=date('now') WHERE id_animal=? AND data_saida IS NULL", (a["id"],))
    conn.execute("INSERT INTO animal_lote (id_animal,id_lote) VALUES (?,?)", (a["id"], l["id"]))
    conn.commit()
    conn.close()
    flash(stdscr, f"Animal {result['Brinco']} movido para {result['Lote']}.")

# ── REPRODUÇÃO ───────────────────────────────
def screen_reproducao(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Coberturas"),
            ("➕", "Registrar Cobertura"),
            ("🔬", "Registrar DG"),
            ("👶", "Registrar Parto"),
            ("⬅️ ", "Voltar"),
        ], title=" Reprodução ", y_off=3, x_off=4, width=34)
        if idx == 0: listar_coberturas(stdscr)
        elif idx == 1: registrar_cobertura(stdscr)
        elif idx == 2: registrar_dg(stdscr)
        elif idx == 3: registrar_parto(stdscr)
        elif idx in (-1, 4): break

def listar_coberturas(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT f.brinco as femea, t.brinco as touro, r.tipo,
               r.data_cobertura, r.resultado_dg, r.data_parto_previsto, r.data_parto_real
        FROM reproducao r JOIN animal f ON r.id_femea=f.id
        LEFT JOIN animal t ON r.id_touro=t.id
        ORDER BY r.data_cobertura DESC LIMIT 100
    """).fetchall()
    conn.close()
    data = [[r["femea"], r["touro"] or "—", r["tipo"], r["data_cobertura"],
             r["resultado_dg"] or "Pendente", r["data_parto_previsto"] or "—",
             r["data_parto_real"] or "—"] for r in rows]
    table_view(stdscr, data, ["Fêmea","Touro","Tipo","Cobertura","DG","Parto Prev.","Parto Real"],
               title=" Reprodução ", col_widths=[8,8,14,11,10,12,12])

def registrar_cobertura(stdscr):
    fields = [
        {"label": "Fêmea (brinco)", "required": True},
        {"label": "Touro (brinco)"},
        {"label": "Tipo", "options": ["Monta Natural","IA","IATF"], "default": "Monta Natural"},
        {"label": "Data", "default": date.today().isoformat()},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Cobertura ", width=55)
    if result is None:
        return
    conn = get_db()
    fid = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Fêmea (brinco)"],)).fetchone()
    if not fid:
        conn.close(); flash(stdscr, "Fêmea não encontrada.", error=True); return
    tid = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Touro (brinco)"],)).fetchone()
    conn.execute("""INSERT INTO reproducao (id_femea,id_touro,tipo,data_cobertura,observacao)
        VALUES (?,?,?,?,?)""",
        (fid["id"], tid["id"] if tid else None,
         result["Tipo"], result["Data"] or date.today().isoformat(),
         result["Obs."] or None))
    conn.commit()
    conn.close()
    flash(stdscr, f"Cobertura registrada para {result['Fêmea (brinco)']}.")

def registrar_dg(stdscr):
    fields = [
        {"label": "Fêmea (brinco)", "required": True},
        {"label": "Resultado", "required": True, "options": ["Positivo","Negativo","Vazia"]},
        {"label": "Data DG",   "default": date.today().isoformat()},
        {"label": "Parto Prev."},
    ]
    result = form(stdscr, fields, title=" Diagnóstico de Gestação ", width=55)
    if result is None:
        return
    conn = get_db()
    fid = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Fêmea (brinco)"],)).fetchone()
    if not fid:
        conn.close(); flash(stdscr, "Fêmea não encontrada.", error=True); return
    conn.execute("""UPDATE reproducao SET resultado_dg=?, data_dg=?, data_parto_previsto=?
        WHERE id_femea=? AND data_dg IS NULL ORDER BY id DESC LIMIT 1""",
        (result["Resultado"], result["Data DG"] or date.today().isoformat(),
         result["Parto Prev."] or None, fid["id"]))
    conn.commit()
    conn.close()
    flash(stdscr, f"DG {result['Resultado']} registrado para {result['Fêmea (brinco)']}.")

def registrar_parto(stdscr):
    fields = [
        {"label": "Fêmea (brinco)", "required": True},
        {"label": "Data parto",     "default": date.today().isoformat()},
        {"label": "Brinco da cria"},
    ]
    result = form(stdscr, fields, title=" Registrar Parto ", width=55)
    if result is None:
        return
    conn = get_db()
    fid = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Fêmea (brinco)"],)).fetchone()
    if not fid:
        conn.close(); flash(stdscr, "Fêmea não encontrada.", error=True); return
    cid = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco da cria"],)).fetchone() if result["Brinco da cria"] else None
    conn.execute("""UPDATE reproducao SET data_parto_real=?, id_cria=?
        WHERE id_femea=? AND data_parto_real IS NULL ORDER BY id DESC LIMIT 1""",
        (result["Data parto"], cid["id"] if cid else None, fid["id"]))
    conn.commit()
    conn.close()
    flash(stdscr, f"Parto registrado para {result['Fêmea (brinco)']}.")

# ── SANIDADE ─────────────────────────────────
def screen_sanidade(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Histórico Sanitário"),
            ("➕", "Novo Procedimento"),
            ("⬅️ ", "Voltar"),
        ], title=" Sanidade ", y_off=3, x_off=4, width=34)
        if idx == 0: historico_sanidade(stdscr)
        elif idx == 1: novo_procedimento(stdscr)
        elif idx in (-1, 2): break

def historico_sanidade(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT s.data, a.brinco as animal, l.nome as lote,
               s.tipo, s.produto, s.dose_ml, s.responsavel
        FROM sanidade s
        LEFT JOIN animal a ON s.id_animal=a.id
        LEFT JOIN lote l ON s.id_lote=l.id
        ORDER BY s.data DESC LIMIT 100
    """).fetchall()
    conn.close()
    data = [[r["data"], r["animal"] or "—", r["lote"] or "—",
             r["tipo"], r["produto"] or "—",
             str(r["dose_ml"]) if r["dose_ml"] else "—",
             r["responsavel"] or "—"] for r in rows]
    table_view(stdscr, data, ["Data","Animal","Lote","Tipo","Produto","Dose","Responsável"],
               title=" Sanidade ", col_widths=[12,8,12,13,16,6,14])

def novo_procedimento(stdscr):
    fields = [
        {"label": "Alvo",       "options": ["animal","lote"], "default": "animal"},
        {"label": "Brinco / Lote", "required": True},
        {"label": "Tipo",       "required": True, "options": ["Vacina","Vermífugo","Carrapaticida","Exame","Outro"]},
        {"label": "Produto",    "required": True},
        {"label": "Dose (ml)"},
        {"label": "Responsável"},
        {"label": "Data",       "default": date.today().isoformat()},
    ]
    result = form(stdscr, fields, title=" Procedimento Sanitário ", width=55)
    if result is None:
        return
    conn = get_db()
    aid = lid = None
    if result["Alvo"] == "animal":
        r = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco / Lote"],)).fetchone()
        if r: aid = r["id"]
        else:
            conn.close(); flash(stdscr, "Animal não encontrado.", error=True); return
    else:
        r = conn.execute("SELECT id FROM lote WHERE nome=?", (result["Brinco / Lote"],)).fetchone()
        if r: lid = r["id"]
        else:
            conn.close(); flash(stdscr, "Lote não encontrado.", error=True); return
    conn.execute("""INSERT INTO sanidade
        (id_animal,id_lote,data,tipo,produto,dose_ml,responsavel)
        VALUES (?,?,?,?,?,?,?)""",
        (aid, lid, result["Data"] or date.today().isoformat(),
         result["Tipo"], result["Produto"],
         float(result["Dose (ml)"]) if result["Dose (ml)"] else None,
         result["Responsável"] or None))
    conn.commit()
    conn.close()
    flash(stdscr, f"{result['Tipo']} de {result['Produto']} registrada.")

# ── PASTOS ───────────────────────────────────
def screen_pastos(stdscr):
    while True:
        idx = menu(stdscr, [
            ("🌿", "Listar Pastos"),
            ("➕", "Cadastrar Pasto"),
            ("⬅️ ", "Voltar"),
        ], title=" Pastos ", y_off=3, x_off=4, width=32)
        if idx == 0: listar_pastos(stdscr)
        elif idx == 1: cadastrar_pasto(stdscr)
        elif idx in (-1, 2): break

def listar_pastos(stdscr):
    conn = get_db()
    rows = conn.execute("SELECT nome, area_ha, forrageira, capacidade_ua FROM pasto ORDER BY nome").fetchall()
    conn.close()
    data = [[r["nome"], r["area_ha"] or "—", r["forrageira"] or "—", r["capacidade_ua"] or "—"] for r in rows]
    table_view(stdscr, data, ["Nome","Área (ha)","Forrageira","Cap. UA"],
               title=" Pastos ", col_widths=[16,10,16,8])

def cadastrar_pasto(stdscr):
    fields = [
        {"label": "Nome",       "required": True},
        {"label": "Área (ha)"},
        {"label": "Forrageira"},
        {"label": "Cap. UA"},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Novo Pasto ", width=50)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("INSERT INTO pasto (nome,area_ha,forrageira,capacidade_ua,observacao) VALUES (?,?,?,?,?)",
                     (result["Nome"],
                      float(result["Área (ha)"]) if result["Área (ha)"] else None,
                      result["Forrageira"] or None,
                      int(result["Cap. UA"]) if result["Cap. UA"] else None,
                      result["Obs."] or None))
        conn.commit()
        flash(stdscr, f"Pasto '{result['Nome']}' cadastrado!")
    except sqlite3.IntegrityError:
        flash(stdscr, f"Pasto '{result['Nome']}' já existe.", error=True)
    finally:
        conn.close()

# ── RELATÓRIOS ───────────────────────────────
def screen_relatorios(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📊", "Resumo do Rebanho"),
            ("⚖️ ", "GMD por Animal"),
            ("❤️ ", "Indicadores Reprodutivos"),
            ("💰", "Financeiro"),
            ("⬅️ ", "Voltar"),
        ], title=" Relatórios ", y_off=3, x_off=4, width=34)
        if idx == 0: relatorio_rebanho(stdscr)
        elif idx == 1: relatorio_gmd(stdscr)
        elif idx == 2: relatorio_prenhez(stdscr)
        elif idx == 3: relatorio_financeiro(stdscr)
        elif idx in (-1, 4): break

def relatorio_rebanho(stdscr):
    conn = get_db()
    rows = conn.execute("""SELECT categoria, sexo, COUNT(*) as qtd FROM animal
        WHERE status='Ativo' GROUP BY categoria, sexo ORDER BY categoria""").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo'").fetchone()[0]
    conn.close()
    data = [[r["categoria"], r["sexo"], r["qtd"]] for r in rows]
    data.append(["─"*10, "─"*4, "─"*4])
    data.append(["TOTAL", "", total])
    table_view(stdscr, data, ["Categoria","Sx","Qtd"],
               title=" Resumo do Rebanho ", col_widths=[14,5,6])

def relatorio_gmd(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT a.brinco, a.categoria,
               MIN(p.data_pesagem) as ini, MAX(p.data_pesagem) as fim,
               MIN(p.peso_kg) as p_ini, MAX(p.peso_kg) as p_fim,
               COUNT(p.id) as n
        FROM pesagem p JOIN animal a ON p.id_animal=a.id
        WHERE a.status='Ativo'
        GROUP BY p.id_animal HAVING n >= 2
        ORDER BY a.brinco
    """).fetchall()
    conn.close()
    data = []
    for r in rows:
        dias = (datetime.fromisoformat(r["fim"]) - datetime.fromisoformat(r["ini"])).days
        gmd = (r["p_fim"] - r["p_ini"]) / dias if dias > 0 else 0
        data.append([r["brinco"], r["categoria"], r["p_ini"], r["p_fim"], f"{gmd:.3f}", dias])
    table_view(stdscr, data, ["Brinco","Categoria","P.Ini","P.Fim","GMD","Dias"],
               title=" GMD por Animal ", col_widths=[8,10,7,7,8,6])

def relatorio_prenhez(stdscr):
    conn = get_db()
    tf = conn.execute("SELECT COUNT(*) FROM animal WHERE sexo='F' AND status='Ativo'").fetchone()[0]
    pr = conn.execute("SELECT COUNT(*) FROM reproducao WHERE resultado_dg='Positivo' AND data_parto_real IS NULL").fetchone()[0]
    pt = conn.execute("SELECT COUNT(*) FROM reproducao WHERE data_parto_real IS NOT NULL").fetchone()[0]
    mo = conn.execute("SELECT COUNT(*) FROM mortalidade").fetchone()[0]
    conn.close()
    taxa = f"{pr/tf*100:.1f}%" if tf > 0 else "—"
    pairs = [
        ("Fêmeas ativas",    tf),
        ("Prenhas (DG+)",    pr),
        ("Partos realizados",pt),
        ("Mortalidade total",mo),
        ("Taxa de prenhez",  taxa),
    ]
    detail_view(stdscr, pairs, title=" Indicadores Reprodutivos ")

def relatorio_financeiro(stdscr):
    conn = get_db()
    c = conn.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0) FROM movimentacao WHERE tipo='Compra'").fetchone()
    v = conn.execute("SELECT COUNT(*), COALESCE(SUM(valor_total),0) FROM movimentacao WHERE tipo='Venda'").fetchone()
    conn.close()
    saldo = v[1] - c[1]
    pairs = [
        ("Compras (qtd)",  c[0]),
        ("Compras (R$)",   f"R$ {c[1]:,.2f}"),
        ("Vendas (qtd)",   v[0]),
        ("Vendas (R$)",    f"R$ {v[1]:,.2f}"),
        ("Saldo",          f"R$ {saldo:,.2f}"),
    ]
    detail_view(stdscr, pairs, title=" Relatório Financeiro ")


# ─────────────────────────────────────────────
# MOVIMENTAÇÕES
# ─────────────────────────────────────────────
def screen_movimentacoes(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Movimentações"),
            ("➕", "Registrar Compra/Venda"),
            ("✏️ ", "Editar Movimentação"),
            ("🗑️ ", "Deletar Movimentação"),
            ("⬅️ ", "Voltar"),
        ], title=" Movimentações ", y_off=3, x_off=4, width=36)
        if idx == 0: listar_movimentacoes(stdscr)
        elif idx == 1: add_movimentacao(stdscr)
        elif idx == 2: editar_movimentacao(stdscr)
        elif idx == 3: deletar_movimentacao(stdscr)
        elif idx in (-1, 4): break

def listar_movimentacoes(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, a.brinco, m.tipo, m.data,
               m.peso_kg, m.valor_arroba, m.valor_total,
               m.contraparte, m.nota_fiscal
        FROM movimentacao m JOIN animal a ON m.id_animal=a.id
        ORDER BY m.data DESC, m.id DESC
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma movimentação registrada.")
        return
    data = [
        [r["id"], r["brinco"], r["tipo"], r["data"],
         f"{r['peso_kg']} kg" if r["peso_kg"] else "—",
         f"R$ {r['valor_arroba']:.2f}" if r["valor_arroba"] else "—",
         f"R$ {r['valor_total']:.2f}" if r["valor_total"] else "—",
         r["contraparte"] or "—"]
        for r in rows
    ]
    idx = table_view(stdscr, data,
                     ["ID","Brinco","Tipo","Data","Peso","R$/@","Total","Contraparte"],
                     title=" Movimentações ",
                     col_widths=[5,8,7,12,9,10,12,16])
    if idx >= 0:
        r = rows[idx]
        pairs = [
            ("ID",           r["id"]),
            ("Brinco",       r["brinco"]),
            ("Tipo",         r["tipo"]),
            ("Data",         r["data"]),
            ("Peso",         f"{r['peso_kg']} kg" if r["peso_kg"] else None),
            ("Valor Arroba", f"R$ {r['valor_arroba']:.2f}" if r["valor_arroba"] else None),
            ("Valor Total",  f"R$ {r['valor_total']:.2f}" if r["valor_total"] else None),
            ("Contraparte",  r["contraparte"]),
            ("Nota Fiscal",  r["nota_fiscal"]),
        ]
        detail_view(stdscr, pairs, title=f" Movimentação #{r['id']} ")

def add_movimentacao(stdscr):
    conn = get_db()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    fields = [
        {"label": "Brinco",       "required": True},
        {"label": "Tipo",         "required": True, "options": ["Compra","Venda"]},
        {"label": "Peso (kg)"},
        {"label": "Valor Arroba", "default": ""},
        {"label": "Contraparte"},
        {"label": "Nota Fiscal"},
        {"label": "Data",         "default": date.today().isoformat()},
        {"label": "Conta",        "options": [""] + contas, "default": ""},
        {"label": "Status",       "options": ["Realizado","Previsto"], "default": "Realizado"},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nova Movimentação ", width=55)
    if result is None:
        return
    conn = get_db()
    a = conn.execute("SELECT id FROM animal WHERE brinco=?", (result["Brinco"],)).fetchone()
    if not a:
        conn.close()
        flash(stdscr, f"Animal {result['Brinco']} não encontrado.", error=True)
        return
    try:
        peso   = float(result["Peso (kg)"])    if result["Peso (kg)"]    else None
        arroba = float(result["Valor Arroba"]) if result["Valor Arroba"] else None
        total  = (peso / 15 * arroba)          if peso and arroba        else None
        data   = result["Data"] or date.today().isoformat()
        tipo_fin = "Despesa" if result["Tipo"] == "Compra" else "Receita"
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone() if result["Conta"] else None
        # Cria lançamento financeiro se houver valor e conta
        lid = None
        if total and id_conta:
            lid = criar_lancamento(
                conn,
                tipo=tipo_fin,
                valor=total,
                descricao=f"{result['Tipo']} de gado — brinco {result['Brinco']}",
                categoria="Gado",
                id_conta=id_conta["id"],
                data=data,
                status=result["Status"],
                origem="movimentacao",
            )
        cur = conn.execute("""INSERT INTO movimentacao
            (id_animal,tipo,data,peso_kg,valor_arroba,valor_total,
             contraparte,nota_fiscal,observacao,id_conta,id_lancamento,status_fin)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (a["id"], result["Tipo"], data,
             peso, arroba, total,
             result["Contraparte"] or None,
             result["Nota Fiscal"] or None,
             result["Obs."] or None,
             id_conta["id"] if id_conta else None,
             lid, result["Status"]))
        # Update lancamento with id_origem now that we have the movimentacao id
        if lid:
            conn.execute("UPDATE fin_lancamento SET id_origem=? WHERE id=?",
                         (cur.lastrowid, lid))
        conn.commit()
        msg = f"{result['Tipo']} registrada para {result['Brinco']}"
        if total:
            msg += f"  |  R$ {total:,.2f}"
        if lid:
            msg += f"  |  Lançamento #{lid}"
        flash(stdscr, msg)
    except ValueError:
        flash(stdscr, "Valor inválido no peso ou arroba.", error=True)
    finally:
        conn.close()

def editar_movimentacao(stdscr):
    # Primeiro exibe a lista para o usuário escolher
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, a.brinco, m.tipo, m.data, m.peso_kg,
               m.valor_arroba, m.valor_total, m.contraparte, m.nota_fiscal
        FROM movimentacao m JOIN animal a ON m.id_animal=a.id
        ORDER BY m.data DESC, m.id DESC
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma movimentação registrada.")
        return
    data = [
        [r["id"], r["brinco"], r["tipo"], r["data"],
         f"{r['peso_kg']} kg" if r["peso_kg"] else "—",
         f"R$ {r['valor_total']:.2f}" if r["valor_total"] else "—",
         r["contraparte"] or "—"]
        for r in rows
    ]
    idx = table_view(stdscr, data,
                     ["ID","Brinco","Tipo","Data","Peso","Total","Contraparte"],
                     title=" Selecionar para Editar ",
                     col_widths=[5,8,7,12,9,12,16])
    if idx < 0:
        return
    r = rows[idx]
    fields = [
        {"label": "Peso (kg)",    "default": str(r["peso_kg"])    if r["peso_kg"]    else ""},
        {"label": "Valor Arroba", "default": str(r["valor_arroba"]) if r["valor_arroba"] else ""},
        {"label": "Data",         "default": r["data"]},
        {"label": "Contraparte",  "default": r["contraparte"] or ""},
        {"label": "Nota Fiscal",  "default": r["nota_fiscal"]  or ""},
    ]
    result = form(stdscr, fields, title=f" Editar #{r['id']} — {r['brinco']} ", width=55)
    if result is None:
        return
    conn = get_db()
    try:
        peso   = float(result["Peso (kg)"])    if result["Peso (kg)"]    else None
        arroba = float(result["Valor Arroba"]) if result["Valor Arroba"] else None
        total  = (peso / 15 * arroba) if peso and arroba else None
        conn.execute("""UPDATE movimentacao
            SET peso_kg=?, valor_arroba=?, valor_total=?,
                data=?, contraparte=?, nota_fiscal=?
            WHERE id=?""",
            (peso, arroba, total,
             result["Data"] or r["data"],
             result["Contraparte"] or None,
             result["Nota Fiscal"] or None,
             r["id"]))
        conn.commit()
        msg = f"Movimentação #{r['id']} atualizada."
        if total:
            msg += f"  |  Novo total: R$ {total:.2f}"
        flash(stdscr, msg)
    except ValueError:
        flash(stdscr, "Valor inválido.", error=True)
    finally:
        conn.close()

def deletar_movimentacao(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, a.brinco, m.tipo, m.data,
               m.valor_total, m.contraparte
        FROM movimentacao m JOIN animal a ON m.id_animal=a.id
        ORDER BY m.data DESC, m.id DESC
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma movimentação registrada.")
        return
    data = [
        [r["id"], r["brinco"], r["tipo"], r["data"],
         f"R$ {r['valor_total']:.2f}" if r["valor_total"] else "—",
         r["contraparte"] or "—"]
        for r in rows
    ]
    idx = table_view(stdscr, data,
                     ["ID","Brinco","Tipo","Data","Total","Contraparte"],
                     title=" Selecionar para Deletar ",
                     col_widths=[5,8,7,12,12,16])
    if idx < 0:
        return
    r = rows[idx]
    h, w = stdscr.getmaxyx()
    if not confirm(stdscr, f"Deletar movimentação #{r['id']} ({r['tipo']} {r['brinco']})?",
                   h//2, max(2, w//2 - 25)):
        return
    conn = get_db()
    conn.execute("DELETE FROM movimentacao WHERE id=?", (r["id"],))
    conn.commit()
    conn.close()
    flash(stdscr, f"Movimentação #{r['id']} deletada.")

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
def screen_dashboard(stdscr):
    """Dashboard como tela própria — aguarda tecla para voltar ao menu."""
    conn = get_db()
    total   = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo'").fetchone()[0]
    femeas  = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo' AND sexo='F'").fetchone()[0]
    machos  = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo' AND sexo='M'").fetchone()[0]
    prenhas = conn.execute("SELECT COUNT(*) FROM reproducao WHERE resultado_dg='Positivo' AND data_parto_real IS NULL").fetchone()[0]
    compras = conn.execute("SELECT COALESCE(SUM(valor_total),0) FROM movimentacao WHERE tipo='Compra'").fetchone()[0]
    vendas  = conn.execute("SELECT COALESCE(SUM(valor_total),0) FROM movimentacao WHERE tipo='Venda'").fetchone()[0]
    saldo   = vendas - compras
    por_cat = conn.execute("""SELECT categoria, COUNT(*) as qtd FROM animal
        WHERE status='Ativo' GROUP BY categoria ORDER BY qtd DESC""").fetchall()
    ult_peso = conn.execute("""
        SELECT a.brinco, p.peso_kg, p.data_pesagem, p.fase FROM pesagem p
        JOIN animal a ON p.id_animal=a.id ORDER BY p.data_pesagem DESC, p.id DESC LIMIT 8
    """).fetchall()
    mortes_mes = conn.execute("""SELECT COUNT(*) FROM mortalidade
        WHERE strftime('%Y-%m', data) = strftime('%Y-%m', 'now')""").fetchone()[0]
    conn.close()

    h, w = stdscr.getmaxyx()
    stdscr.erase()
    draw_header(stdscr)
    draw_footer(stdscr, "Q/Enter voltar ao menu")

    # ── Linha de KPIs ──────────────────────────────────────────
    kpis = [
        ("Rebanho Ativo", str(total)),
        ("Fêmeas",        str(femeas)),
        ("Machos",        str(machos)),
        ("Prenhas",       str(prenhas)),
        ("Mortes/mês",    str(mortes_mes)),
        ("Saldo",         f"R$ {saldo:,.0f}"),
    ]
    n = len(kpis)
    bw = max(12, min(16, (w - 4) // n))
    for i, (lbl, val) in enumerate(kpis):
        x = 2 + i * (bw + 1)
        if x + bw > w - 1:
            break
        # desenha diretamente em stdscr sem subwindow
        safe_addstr(stdscr, 2, x, ("─" * (bw - 2)).center(bw), INFO())
        safe_addstr(stdscr, 3, x, lbl[:bw].center(bw), TITLE())
        color = ERROR() if (lbl == "Saldo" and saldo < 0) or (lbl == "Mortes/mês" and mortes_mes > 0) else SUCCESS()
        safe_addstr(stdscr, 4, x, val[:bw].center(bw), color)
        safe_addstr(stdscr, 5, x, ("─" * (bw - 2)).center(bw), INFO())

    # ── Por categoria ───────────────────────────────────────────
    col1_x = 2
    safe_addstr(stdscr, 7, col1_x, " Rebanho por Categoria ", HEADER())
    for i, r in enumerate(por_cat):
        if 8 + i >= h - 4:
            break
        bar_max = 20
        bar_len = int(r["qtd"] / max(total, 1) * bar_max)
        bar = "█" * bar_len + "░" * (bar_max - bar_len)
        safe_addstr(stdscr, 8 + i, col1_x,
                    f"  {r['categoria']:<10} {bar} {r['qtd']}",
                    NORMAL())

    # ── Últimas pesagens ────────────────────────────────────────
    col2_x = min(w // 2, 42)
    safe_addstr(stdscr, 7, col2_x, " Últimas Pesagens ", HEADER())
    if ult_peso:
        for i, p in enumerate(ult_peso):
            if 8 + i >= h - 4:
                break
            fase = f"[{p['fase']}]" if p["fase"] else "      "
            safe_addstr(stdscr, 8 + i, col2_x,
                        f"  {p['brinco']:<8} {p['peso_kg']:>6.1f} kg  {fase}  {p['data_pesagem']}",
                        NORMAL())
    else:
        safe_addstr(stdscr, 8, col2_x, "  Nenhuma pesagem registrada.", WARN())

    stdscr.refresh()
    # Aguarda tecla
    while True:
        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27, curses.KEY_ENTER, 10, 13):
            break


def draw_dashboard(stdscr):
    """Versão resumida para fundo do menu principal."""
    h, w = stdscr.getmaxyx()
    draw_header(stdscr)

    conn = get_db()
    total   = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo'").fetchone()[0]
    femeas  = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo' AND sexo='F'").fetchone()[0]
    machos  = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo' AND sexo='M'").fetchone()[0]
    prenhas = conn.execute("SELECT COUNT(*) FROM reproducao WHERE resultado_dg='Positivo' AND data_parto_real IS NULL").fetchone()[0]
    compras = conn.execute("SELECT COALESCE(SUM(valor_total),0) FROM movimentacao WHERE tipo='Compra'").fetchone()[0]
    vendas  = conn.execute("SELECT COALESCE(SUM(valor_total),0) FROM movimentacao WHERE tipo='Venda'").fetchone()[0]
    ult_peso = conn.execute("""
        SELECT a.brinco, p.peso_kg, p.data_pesagem FROM pesagem p
        JOIN animal a ON p.id_animal=a.id ORDER BY p.data_pesagem DESC, p.id DESC LIMIT 4
    """).fetchall()
    conn.close()

    # KPIs numa linha
    kpis = [
        ("Rebanho", str(total)),
        ("Fêmeas",  str(femeas)),
        ("Machos",  str(machos)),
        ("Prenhas", str(prenhas)),
        ("Saldo",   f"R${vendas-compras:,.0f}"),
    ]
    y = 2
    x = 2
    for lbl, val in kpis:
        txt = f"{lbl}: {val}   "
        if x + len(txt) > w - 2:
            break
        safe_addstr(stdscr, y, x, lbl + ": ", TITLE())
        safe_addstr(stdscr, y, x + len(lbl) + 2, val + "   ", INFO())
        x += len(txt)

    # Últimas pesagens abaixo
    if ult_peso:
        safe_addstr(stdscr, 4, 2, "Últimas pesagens:", TITLE())
        for i, p in enumerate(ult_peso):
            safe_addstr(stdscr, 5 + i, 4,
                        f"{p['brinco']:<8}  {p['peso_kg']:>6.1f} kg   {p['data_pesagem']}",
                        NORMAL())

    stdscr.refresh()

# ═════════════════════════════════════════════════════
# MÓDULO: FINANCEIRO
# ═════════════════════════════════════════════════════
def screen_financeiro(stdscr):
    while True:
        idx = menu(stdscr, [
            ("🏦", "Contas Bancárias"),
            ("📋", "Lançamentos"),
            ("🔍", "Filtrar Lançamentos"),
            ("➕", "Novo Lançamento"),
            ("🗑️ ", "Apagar Lançamento"),
            ("📊", "Resultado Anual"),
            ("⬅️ ", "Voltar"),
        ], title=" Financeiro ", y_off=3, x_off=4, width=34)
        if idx == 0: screen_contas(stdscr)
        elif idx == 1: listar_lancamentos(stdscr)
        elif idx == 2: filtrar_lancamentos(stdscr)
        elif idx == 3: novo_lancamento(stdscr)
        elif idx == 4: apagar_lancamento(stdscr)
        elif idx == 5: resultado_anual(stdscr)
        elif idx in (-1, 6): break

# ── Contas ──────────────────────────────────────────
def screen_contas(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Contas"),
            ("➕", "Nova Conta"),
            ("✏️ ", "Editar Conta"),
            ("⬅️ ", "Voltar"),
        ], title=" Contas Bancárias ", y_off=3, x_off=4, width=32)
        if idx == 0: listar_contas(stdscr)
        elif idx == 1: nova_conta(stdscr)
        elif idx == 2: editar_conta(stdscr)
        elif idx in (-1, 3): break

def listar_contas(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT c.id, c.nome, c.banco, c.numero, c.saldo_inicial,
               COALESCE(SUM(CASE WHEN l.tipo='Receita' AND l.status='Realizado' THEN l.valor ELSE 0 END),0)
               - COALESCE(SUM(CASE WHEN l.tipo='Despesa' AND l.status='Realizado' THEN l.valor ELSE 0 END),0)
               + c.saldo_inicial AS saldo_atual
        FROM fin_conta c
        LEFT JOIN fin_lancamento l ON l.id_conta = c.id
        WHERE c.ativa=1
        GROUP BY c.id ORDER BY c.nome
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma conta cadastrada.")
        return
    data = [[r["nome"], r["banco"] or "—", r["numero"] or "—",
             f"R$ {r['saldo_inicial']:,.2f}",
             f"R$ {r['saldo_atual']:,.2f}"] for r in rows]
    table_view(stdscr, data,
               ["Nome", "Banco", "Número", "Saldo Inicial", "Saldo Atual"],
               title=" Contas ", col_widths=[18, 14, 12, 15, 15])

def nova_conta(stdscr):
    fields = [
        {"label": "Nome",          "required": True},
        {"label": "Banco"},
        {"label": "Agência"},
        {"label": "Número"},
        {"label": "Saldo Inicial", "default": "0"},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nova Conta ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("""INSERT INTO fin_conta (nome, banco, agencia, numero, saldo_inicial, observacao)
            VALUES (?,?,?,?,?,?)""",
            (result["Nome"], result["Banco"] or None, result["Agência"] or None,
             result["Número"] or None,
             float(result["Saldo Inicial"]) if result["Saldo Inicial"] else 0,
             result["Obs."] or None))
        conn.commit()
        flash(stdscr, f"Conta '{result['Nome']}' criada!")
    except sqlite3.IntegrityError:
        flash(stdscr, f"Conta '{result['Nome']}' já existe.", error=True)
    except ValueError:
        flash(stdscr, "Saldo inicial inválido.", error=True)
    finally:
        conn.close()

def editar_conta(stdscr):
    conn = get_db()
    contas = conn.execute("SELECT id, nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()
    conn.close()
    if not contas:
        flash(stdscr, "Nenhuma conta cadastrada.")
        return
    nomes = [r["nome"] for r in contas]
    idx = option_picker(stdscr, nomes, "Escolher Conta", 5, 10)
    if idx is None:
        return
    conn = get_db()
    c = conn.execute("SELECT * FROM fin_conta WHERE id=?", (contas[idx]["id"],)).fetchone()
    conn.close()
    fields = [
        {"label": "Nome",          "default": c["nome"],                   "required": True},
        {"label": "Banco",         "default": c["banco"] or ""},
        {"label": "Agência",       "default": c["agencia"] or ""},
        {"label": "Número",        "default": c["numero"] or ""},
        {"label": "Saldo Inicial", "default": str(c["saldo_inicial"])},
        {"label": "Obs.",          "default": c["observacao"] or ""},
    ]
    result = form(stdscr, fields, title=f" Editar: {c['nome']} ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("""UPDATE fin_conta SET nome=?, banco=?, agencia=?, numero=?,
            saldo_inicial=?, observacao=? WHERE id=?""",
            (result["Nome"], result["Banco"] or None, result["Agência"] or None,
             result["Número"] or None,
             float(result["Saldo Inicial"]) if result["Saldo Inicial"] else 0,
             result["Obs."] or None, c["id"]))
        conn.commit()
        flash(stdscr, f"Conta atualizada.")
    except ValueError:
        flash(stdscr, "Saldo inicial inválido.", error=True)
    finally:
        conn.close()

def filtrar_lancamentos(stdscr):
    """
    Tela de filtros para lançamentos financeiros.
    Usa o form() padrão — todos os filtros são campos opcionais.
    """
    conn = get_db()
    contas_db = ["(todas)"] + [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta ORDER BY nome").fetchall()]
    conn.close()

    fields = [
        {"label": "Data início",       "default": ""},
        {"label": "Data fim",          "default": ""},
        {"label": "Tipo",              "options": ["(todos)", "Receita", "Despesa"],
         "default": "(todos)"},
        {"label": "Operador valor",    "options": ["(qualquer)", ">", ">=", "=", "<=", "<"],
         "default": "(qualquer)"},
        {"label": "Valor (R$)",        "default": ""},
        {"label": "Categoria",
         "options": ["(todas)", "Gado", "Eucalipto", "Equipamento", "Geral"],
         "default": "(todas)"},
        {"label": "Status",            "options": ["(todos)", "Realizado", "Previsto"],
         "default": "(todos)"},
        {"label": "Conta",             "options": contas_db, "default": "(todas)"},
        {"label": "Descrição contém",   "default": ""},
        {"label": "Beneficiário contém", "default": ""},
    ]

    result = form(stdscr, fields, title=" Filtrar Lançamentos ", width=52)
    if result is None:
        return

    # Monta query dinamicamente
    conditions = []
    params     = []

    if result["Data início"].strip():
        conditions.append("l.data >= ?")
        params.append(result["Data início"].strip())

    if result["Data fim"].strip():
        conditions.append("l.data <= ?")
        params.append(result["Data fim"].strip())

    if result["Tipo"] != "(todos)":
        conditions.append("l.tipo = ?")
        params.append(result["Tipo"])

    op = result["Operador valor"]
    if op != "(qualquer)" and result["Valor (R$)"].strip():
        try:
            v = float(result["Valor (R$)"].replace(",", "."))
            conditions.append(f"l.valor {op} ?")
            params.append(v)
        except ValueError:
            pass

    if result["Categoria"] != "(todas)":
        conditions.append("l.categoria = ?")
        params.append(result["Categoria"])

    if result["Status"] != "(todos)":
        conditions.append("l.status = ?")
        params.append(result["Status"])

    if result["Conta"] != "(todas)":
        conditions.append("c.nome = ?")
        params.append(result["Conta"])

    if result["Descrição contém"].strip():
        conditions.append("l.descricao LIKE ?")
        params.append(f"%{result['Descrição contém'].strip()}%")

    if result["Beneficiário contém"].strip():
        conditions.append("l.beneficiario LIKE ?")
        params.append(f"%{result['Beneficiário contém'].strip()}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    rows = conn.execute(f"""
        SELECT l.id, l.data, l.data_pagamento, l.tipo, l.valor, l.descricao,
               l.beneficiario, l.categoria, l.status, l.origem, l.observacao, c.nome as conta
        FROM fin_lancamento l
        LEFT JOIN fin_conta c ON l.id_conta = c.id
        {where}
        ORDER BY l.data DESC, l.id DESC
    """, params).fetchall()
    conn.close()

    if not rows:
        flash(stdscr, "Nenhum lançamento encontrado com esses filtros.")
        return

    receitas  = sum(r["valor"] for r in rows if r["tipo"] == "Receita")
    despesas  = sum(r["valor"] for r in rows if r["tipo"] == "Despesa")
    saldo     = receitas - despesas
    titulo    = f" Filtro: {len(rows)} reg.  +R${receitas:,.0f}  -R${despesas:,.0f}  ={saldo:+,.0f} "

    data = [[r["id"], r["data"], r["tipo"], f"R$ {r['valor']:,.2f}",
             r["descricao"][:35], r["categoria"], r["status"], r["conta"] or "—"]
            for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Data","Tipo","Valor","Descrição","Categoria","Status","Conta"],
                     title=titulo,
                     col_widths=[5,12,8,12,37,11,10,14])
    if idx >= 0:
        r = rows[idx]
        pairs = [
            ("ID",        r["id"]),
            ("Data",      r["data"]),
            ("Pagamento", r["data_pagamento"]),
            ("Tipo",      r["tipo"]),
            ("Valor",     f"R$ {r['valor']:,.2f}"),
            ("Descrição",    r["descricao"]),
            ("Beneficiário", r["beneficiario"] or "—"),
            ("Categoria",    r["categoria"]),
            ("Conta",     r["conta"]),
            ("Status",    r["status"]),
            ("Origem",    r["origem"]),
            ("Obs.",      r["observacao"]),
        ]
        detail_view(stdscr, pairs, title=f" Lançamento #{r['id']} ")


# ── Lançamentos ─────────────────────────────────────
def listar_lancamentos(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT l.id, l.data, l.data_pagamento, l.tipo, l.valor, l.descricao,
               l.beneficiario, l.categoria, l.status, l.origem, l.observacao, c.nome as conta
        FROM fin_lancamento l
        LEFT JOIN fin_conta c ON l.id_conta = c.id
        ORDER BY l.data DESC, l.id DESC LIMIT 200
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhum lançamento registrado.")
        return
    data = [[r["id"], r["data"], r["tipo"], f"R$ {r['valor']:,.2f}",
             r["descricao"][:40], r["beneficiario"][:18] if r["beneficiario"] else "—",
             r["categoria"], r["status"], r["conta"] or "—"]
            for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Data","Tipo","Valor","Descrição","Beneficiário","Categoria","Status","Conta"],
                     title=" Lançamentos ", col_widths=[5,12,8,12,42,20,11,10,14])
    if idx >= 0:
        _editar_lancamento_inline(stdscr, rows[idx]["id"])

def novo_lancamento(stdscr, prefill=None, title=" Novo Lançamento "):
    """Cria lançamento manual. prefill = dict com defaults."""
    conn = get_db()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    p = prefill or {}
    fields = [
        {"label": "Tipo",          "required": True,
         "options": ["Receita","Despesa"], "default": p.get("tipo","Despesa")},
        {"label": "Valor",         "required": True, "default": p.get("valor","")},
        {"label": "Descrição",     "required": True, "default": p.get("descricao","")},
        {"label": "Beneficiário",  "default": p.get("beneficiario","")},
        {"label": "Categoria",     "options": ["Gado","Eucalipto","Equipamento","Geral"],
         "default": p.get("categoria","Geral")},
        {"label": "Conta",         "options": contas, "default": p.get("conta", contas[0] if contas else "")},
        {"label": "Data",          "default": p.get("data", date.today().isoformat())},
        {"label": "Pagamento",     "default": p.get("pagamento","")},
        {"label": "Status",        "options": ["Previsto","Realizado"], "default": p.get("status","Previsto")},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=title, width=56)
    if result is None:
        return None
    conn = get_db()
    try:
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone()
        lid = criar_lancamento(
            conn,
            tipo=result["Tipo"],
            valor=float(result["Valor"]),
            descricao=result["Descrição"],
            beneficiario=result["Beneficiário"] or None,
            categoria=result["Categoria"],
            id_conta=id_conta["id"] if id_conta else None,
            data=result["Data"] or date.today().isoformat(),
            data_pagamento=result["Pagamento"] or None,
            status=result["Status"],
        )
        conn.commit()
        flash(stdscr, f"Lançamento #{lid} criado: R$ {float(result['Valor']):,.2f}")
        return lid
    except ValueError:
        flash(stdscr, "Valor inválido.", error=True)
        return None
    finally:
        conn.close()

def _editar_lancamento_inline(stdscr, lancamento_id):
    """Edita um lançamento diretamente pelo id, sem tela de seleção."""
    conn = get_db()
    r = conn.execute("""
        SELECT l.id, l.data, l.tipo, l.valor, l.descricao, l.beneficiario,
               l.categoria, l.status, l.data_pagamento, l.observacao,
               c.nome as conta, l.id_conta
        FROM fin_lancamento l
        LEFT JOIN fin_conta c ON l.id_conta = c.id
        WHERE l.id=?
    """, (lancamento_id,)).fetchone()
    contas = [rc["nome"] for rc in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not r:
        flash(stdscr, f"Lançamento #{lancamento_id} não encontrado.", error=True)
        return
    fields = [
        {"label": "Tipo",          "options": ["Receita","Despesa"], "default": r["tipo"]},
        {"label": "Valor",         "default": str(r["valor"]),       "required": True},
        {"label": "Descrição",     "default": r["descricao"],        "required": True},
        {"label": "Beneficiário",  "default": r["beneficiario"] or ""},
        {"label": "Categoria",     "options": ["Gado","Eucalipto","Equipamento","Geral"],
         "default": r["categoria"]},
        {"label": "Conta",         "options": contas, "default": r["conta"] or ""},
        {"label": "Data",          "default": r["data"]},
        {"label": "Pagamento",     "default": r["data_pagamento"] or ""},
        {"label": "Status",        "options": ["Previsto","Realizado"], "default": r["status"]},
        {"label": "Obs.",          "default": r["observacao"] or ""},
    ]
    result = form(stdscr, fields, title=f" Editar Lançamento #{r['id']} ", width=56)
    if result is None:
        return
    conn = get_db()
    try:
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone()
        conn.execute("""UPDATE fin_lancamento SET
            tipo=?, valor=?, descricao=?, beneficiario=?, categoria=?, id_conta=?,
            data=?, data_pagamento=?, status=?, observacao=?
            WHERE id=?""",
            (result["Tipo"], float(result["Valor"]), result["Descrição"],
             result["Beneficiário"] or None,
             result["Categoria"],
             id_conta["id"] if id_conta else None,
             result["Data"] or r["data"],
             result["Pagamento"] or None,
             result["Status"],
             result["Obs."] or None,
             r["id"]))
        conn.commit()
        flash(stdscr, f"Lançamento #{r['id']} atualizado.")
    except ValueError:
        flash(stdscr, "Valor inválido.", error=True)
    finally:
        conn.close()


def apagar_lancamento(stdscr):
    """Remove um lançamento financeiro após confirmação."""
    conn = get_db()
    rows = conn.execute("""
        SELECT l.id, l.data, l.tipo, l.valor, l.descricao, l.status, l.origem
        FROM fin_lancamento l
        ORDER BY l.data DESC, l.id DESC LIMIT 200
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhum lançamento registrado.")
        return
    data = [[r["id"], r["data"], r["tipo"], f"R$ {r['valor']:,.2f}",
             r["descricao"][:28], r["status"]] for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Data","Tipo","Valor","Descrição","Status"],
                     title=" Selecionar Lançamento para Apagar ",
                     col_widths=[5,12,8,12,30,10])
    if idx < 0:
        return
    r = rows[idx]
    h, w = stdscr.getmaxyx()
    aviso = ""
    if r["origem"]:
        aviso = f" (gerado por {r['origem']})"
    if not confirm(stdscr,
                   f"Apagar #{r['id']} R$ {r['valor']:,.2f}{aviso}?",
                   h//2, max(2, w//2 - 28)):
        return
    conn = get_db()
    conn.execute("DELETE FROM fin_lancamento WHERE id=?", (r["id"],))
    conn.commit()
    conn.close()
    flash(stdscr, f"Lançamento #{r['id']} apagado.")


def resultado_anual(stdscr):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 30, h//2-2, w//2-15)
    win.erase(); draw_box(win, " Ano ")
    safe_addstr(win, 2, 2, "Ano (ex: 2025): ", TITLE())
    win.refresh()
    ano = text_input(win, 2, 18, 8, str(date.today().year))
    if not ano:
        return
    conn = get_db()
    categorias = ["Gado", "Eucalipto", "Equipamento", "Geral"]
    pairs = [("── RESULTADO ANUAL " + ano + " ──", "")]
    total_rec = total_des = 0
    for cat in categorias:
        rec = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
            WHERE tipo='Receita' AND status='Realizado' AND categoria=?
            AND strftime('%Y',data)=?""", (cat, ano)).fetchone()[0]
        des = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
            WHERE tipo='Despesa' AND status='Realizado' AND categoria=?
            AND strftime('%Y',data)=?""", (cat, ano)).fetchone()[0]
        res = rec - des
        pairs.append((f"── {cat} ──", ""))
        pairs.append(("  Receitas",  f"R$ {rec:,.2f}"))
        pairs.append(("  Despesas",  f"R$ {des:,.2f}"))
        pairs.append(("  Resultado", f"R$ {res:,.2f}"))
        total_rec += rec
        total_des += des
    pairs.append(("── CONSOLIDADO ──", ""))
    pairs.append(("  Total Receitas", f"R$ {total_rec:,.2f}"))
    pairs.append(("  Total Despesas", f"R$ {total_des:,.2f}"))
    pairs.append(("  Resultado Geral", f"R$ {total_rec-total_des:,.2f}"))
    conn.close()
    detail_view(stdscr, pairs, title=f" Resultado {ano} ")


# ═════════════════════════════════════════════════════
# MÓDULO: EUCALIPTO
# ═════════════════════════════════════════════════════
def screen_eucalipto(stdscr):
    while True:
        idx = menu(stdscr, [
            ("🌲", "Talhões"),
            ("📦", "Safras"),
            ("🚚", "Cargas"),
            ("💸", "Despesas de Safra"),
            ("🧪", "Movimentações de Talhão"),
            ("📈", "Inventário"),
            ("⚙️ ", "Curva de Crescimento"),
            ("⬅️ ", "Voltar"),
        ], title=" Eucalipto ", y_off=3, x_off=4, width=36)
        if idx == 0: screen_talhoes(stdscr)
        elif idx == 1: screen_safras(stdscr)
        elif idx == 2: screen_cargas(stdscr)
        elif idx == 3: screen_despesas_safra(stdscr)
        elif idx == 4: screen_mov_talhao(stdscr)
        elif idx == 5: screen_inventario(stdscr)
        elif idx == 6: screen_curva(stdscr)
        elif idx in (-1, 7): break

# ── Talhões ──────────────────────────────────────────
def screen_talhoes(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Talhões"),
            ("➕", "Novo Talhão"),
            ("✏️ ", "Editar Talhão"),
            ("⬅️ ", "Voltar"),
        ], title=" Talhões ", y_off=3, x_off=4, width=30)
        if idx == 0: listar_talhoes(stdscr)
        elif idx == 1: novo_talhao(stdscr)
        elif idx == 2: editar_talhao(stdscr)
        elif idx in (-1, 3): break

def listar_talhoes(stdscr):
    conn = get_db()
    rows = conn.execute(
        "SELECT id, nome, area_ha, data_plantio, clone, status FROM eu_talhao ORDER BY nome"
    ).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhum talhão cadastrado.")
        return
    data = [[r["nome"], r["area_ha"], r["data_plantio"] or "—",
             r["clone"] or "—", r["status"]] for r in rows]
    idx = table_view(stdscr, data,
                     ["Nome","Área(ha)","Plantio","Clone","Status"],
                     title=" Talhões ", col_widths=[14,9,12,14,11])
    if idx >= 0:
        # Mostra detalhe com inventário
        conn = get_db()
        r = rows[idx]
        vol = inventario_talhao(conn, r["id"])
        conn.close()
        obs_row = conn.execute("SELECT observacao FROM eu_talhao WHERE id=?", (r["id"],))
        pairs = [
            ("Nome",       r["nome"]),
            ("Área",       f"{r['area_ha']} ha"),
            ("Data Plantio", r["data_plantio"]),
            ("Clone",      r["clone"]),
            ("Status",     r["status"]),
            ("Volume Estimado Hoje", f"{vol} m³" if vol is not None else "Sem dados"),
        ]
        detail_view(stdscr, pairs, title=f" Talhão: {r['nome']} ")

def novo_talhao(stdscr):
    fields = [
        {"label": "Nome",         "required": True},
        {"label": "Área (ha)",    "required": True},
        {"label": "Data Plantio", "default": ""},
        {"label": "Clone"},
        {"label": "Status", "options": ["Crescendo","Colhido","Reforma","Inativo"],
         "default": "Crescendo"},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Novo Talhão ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("""INSERT INTO eu_talhao (nome, area_ha, data_plantio, clone, status, observacao)
            VALUES (?,?,?,?,?,?)""",
            (result["Nome"], float(result["Área (ha)"]),
             result["Data Plantio"] or None, result["Clone"] or None,
             result["Status"], result["Obs."] or None))
        conn.commit()
        flash(stdscr, f"Talhão '{result['Nome']}' cadastrado!")
    except (sqlite3.IntegrityError, ValueError) as e:
        flash(stdscr, f"Erro: {e}", error=True)
    finally:
        conn.close()

def editar_talhao(stdscr):
    conn = get_db()
    talhoes = conn.execute("SELECT id, nome FROM eu_talhao ORDER BY nome").fetchall()
    conn.close()
    if not talhoes:
        flash(stdscr, "Nenhum talhão cadastrado.")
        return
    idx = option_picker(stdscr, [r["nome"] for r in talhoes], "Escolher Talhão", 5, 10)
    if idx is None:
        return
    conn = get_db()
    t = conn.execute("SELECT * FROM eu_talhao WHERE id=?", (talhoes[idx]["id"],)).fetchone()
    conn.close()
    fields = [
        {"label": "Nome",         "default": t["nome"],                    "required": True},
        {"label": "Área (ha)",    "default": str(t["area_ha"])},
        {"label": "Data Plantio", "default": t["data_plantio"] or ""},
        {"label": "Clone",        "default": t["clone"] or ""},
        {"label": "Status",       "default": t["status"],
         "options": ["Crescendo","Colhido","Reforma","Inativo"]},
        {"label": "Obs.",         "default": t["observacao"] or ""},
    ]
    result = form(stdscr, fields, title=f" Editar: {t['nome']} ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("""UPDATE eu_talhao SET nome=?, area_ha=?, data_plantio=?,
            clone=?, status=?, observacao=? WHERE id=?""",
            (result["Nome"], float(result["Área (ha)"]),
             result["Data Plantio"] or None, result["Clone"] or None,
             result["Status"], result["Obs."] or None, t["id"]))
        conn.commit()
        flash(stdscr, "Talhão atualizado.")
    except ValueError:
        flash(stdscr, "Área inválida.", error=True)
    finally:
        conn.close()

# ── Safras ───────────────────────────────────────────
def screen_safras(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Safras"),
            ("➕", "Nova Safra"),
            ("✏️ ", "Editar Safra"),
            ("⬅️ ", "Voltar"),
        ], title=" Safras ", y_off=3, x_off=4, width=30)
        if idx == 0: listar_safras(stdscr)
        elif idx == 1: nova_safra(stdscr)
        elif idx == 2: editar_safra(stdscr)
        elif idx in (-1, 3): break

def listar_safras(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.codigo, s.status, s.data_inicio, s.data_fim,
               COUNT(c.id) as n_cargas,
               COALESCE(SUM(c.volume_m3),0) as vol_total,
               COALESCE(SUM(c.valor_total),0) as rec_total
        FROM eu_safra s
        LEFT JOIN eu_carga c ON c.id_safra=s.id
        GROUP BY s.id ORDER BY s.codigo DESC
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma safra cadastrada.")
        return
    data = [[r["codigo"], r["status"], r["data_inicio"] or "—",
             r["n_cargas"], f"{r['vol_total']:.1f} m³",
             f"R$ {r['rec_total']:,.0f}"] for r in rows]
    idx = table_view(stdscr, data,
                     ["Código","Status","Início","Cargas","Volume","Receita"],
                     title=" Safras ", col_widths=[8,11,12,7,12,14])
    if idx >= 0:
        _detalhe_safra(stdscr, rows[idx])

def _detalhe_safra(stdscr, s):
    conn = get_db()
    cargas = conn.execute("""
        SELECT id, numero, data_saida, data_romaneio, volume_m3,
               valor_unitario, valor_total, status, data_recebimento
        FROM eu_carga WHERE id_safra=? ORDER BY COALESCE(data_saida,'9999')
    """, (s["id"],)).fetchall()
    # Despesas diretas da safra por categoria
    desp_cats = conn.execute("""
        SELECT categoria,
               COALESCE(SUM(CASE WHEN status='Realizado' THEN valor ELSE 0 END),0) as realizado,
               COALESCE(SUM(CASE WHEN status='Previsto'  THEN valor ELSE 0 END),0) as previsto
        FROM eu_despesa_safra
        WHERE id_safra=?
        GROUP BY categoria ORDER BY categoria
    """, (s["id"],)).fetchall()
    desp_total = conn.execute("""
        SELECT COALESCE(SUM(CASE WHEN status='Realizado' THEN valor ELSE 0 END),0)
        FROM eu_despesa_safra WHERE id_safra=?
    """, (s["id"],)).fetchone()[0]
    conn.close()

    pairs = [
        ("── SAFRA " + s["codigo"] + " ──", ""),
        ("Status",  s["status"]),
        ("Início",  s["data_inicio"]),
        ("Fim",     s["data_fim"]),
        ("── CARGAS (" + str(len(cargas)) + ") ──", ""),
    ]
    vol_total = rec_total = 0
    for c in cargas:
        vol = c["volume_m3"] or 0
        val = c["valor_total"] or 0
        vol_total += vol
        rec_total += val
        linha = f"#{c['id']} {c['status']:<10}"
        if c["data_saida"]:       linha += f"  Saída:{c['data_saida']}"
        if c["volume_m3"]:        linha += f"  {c['volume_m3']}m³"
        if c["valor_total"]:      linha += f"  R${c['valor_total']:,.0f}"
        if c["data_recebimento"]: linha += f"  ✓{c['data_recebimento']}"
        pairs.append(("  ", linha))
    pairs.append(("── DESPESAS ──", ""))
    if desp_cats:
        for dc in desp_cats:
            pairs.append((f"  {dc['categoria']}",
                          f"R$ {dc['realizado']:,.2f}" +
                          (f"  (+ R$ {dc['previsto']:,.2f} previsto)" if dc["previsto"] else "")))
    else:
        pairs.append(("  (sem despesas registradas)", ""))
    pairs.append(("── CONSOLIDADO ──", ""))
    pairs.append(("  Volume Total",   f"{vol_total:.1f} m³"))
    pairs.append(("  Receita Total",  f"R$ {rec_total:,.2f}"))
    pairs.append(("  Despesas",       f"R$ {desp_total:,.2f}"))
    pairs.append(("  Resultado",      f"R$ {rec_total - desp_total:,.2f}"))
    detail_view(stdscr, pairs, title=f" Safra {s['codigo']} ")

def nova_safra(stdscr):
    fields = [
        {"label": "Código",      "required": True, "default": ""},
        {"label": "Descrição"},
        {"label": "Data Início", "default": ""},
        {"label": "Data Fim",    "default": ""},
        {"label": "Status", "options": ["Planejada","Ativa","Concluída"], "default": "Planejada"},
    ]
    result = form(stdscr, fields, title=" Nova Safra ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("""INSERT INTO eu_safra (codigo, descricao, data_inicio, data_fim, status)
            VALUES (?,?,?,?,?)""",
            (result["Código"], result["Descrição"] or None,
             result["Data Início"] or None, result["Data Fim"] or None,
             result["Status"]))
        conn.commit()
        flash(stdscr, f"Safra '{result['Código']}' criada!")
    except sqlite3.IntegrityError:
        flash(stdscr, f"Safra '{result['Código']}' já existe.", error=True)
    finally:
        conn.close()

def editar_safra(stdscr):
    conn = get_db()
    safras = conn.execute("SELECT id, codigo FROM eu_safra ORDER BY codigo DESC").fetchall()
    conn.close()
    if not safras:
        flash(stdscr, "Nenhuma safra cadastrada.")
        return
    idx = option_picker(stdscr, [r["codigo"] for r in safras], "Escolher Safra", 5, 10)
    if idx is None:
        return
    conn = get_db()
    s = conn.execute("SELECT * FROM eu_safra WHERE id=?", (safras[idx]["id"],)).fetchone()
    conn.close()
    fields = [
        {"label": "Código",      "default": s["codigo"],           "required": True},
        {"label": "Descrição",   "default": s["descricao"] or ""},
        {"label": "Data Início", "default": s["data_inicio"] or ""},
        {"label": "Data Fim",    "default": s["data_fim"] or ""},
        {"label": "Status",      "default": s["status"],
         "options": ["Planejada","Ativa","Concluída"]},
    ]
    result = form(stdscr, fields, title=f" Editar Safra {s['codigo']} ", width=52)
    if result is None:
        return
    conn = get_db()
    conn.execute("""UPDATE eu_safra SET codigo=?, descricao=?, data_inicio=?, data_fim=?, status=?
        WHERE id=?""",
        (result["Código"], result["Descrição"] or None,
         result["Data Início"] or None, result["Data Fim"] or None,
         result["Status"], s["id"]))
    conn.commit()
    conn.close()
    flash(stdscr, "Safra atualizada.")

# ── Cargas ───────────────────────────────────────────
def screen_cargas(stdscr):
    """Tela principal de cargas: listagem + ações integradas."""
    while True:
        # Recarrega a cada iteração para refletir alterações
        conn = get_db()
        rows = conn.execute("""
            SELECT c.id, s.codigo as safra, c.placa, c.data_saida,
                   c.tipo_carga, c.nome_cliente, c.codigo_romaneio,
                   c.data_romaneio, c.volume_m3, c.data_recebimento,
                   c.valor_recebido, c.percentual_recebido, c.desconto, c.preco_m3,
                   c.valor_total, c.id_lancamento, c.observacao, c.status
            FROM eu_carga c JOIN eu_safra s ON c.id_safra=s.id
            ORDER BY
                CASE WHEN c.data_romaneio IS NULL THEN 0 ELSE 1 END,
                COALESCE(c.data_saida,'9999') DESC
        """).fetchall()
        conn.close()

        if not rows:
            idx = menu(stdscr, [
                ("➕", "Registrar Saída de Carga"),
                ("⬅️ ", "Voltar"),
            ], title=" Cargas de Carvão ", y_off=3, x_off=4, width=34)
            if idx == 0: _registrar_saida(stdscr)
            else: break
            continue

        # Monta tabela: * = sem romaneio
        def _fmt(v): return f"R${v:,.0f}" if v else ""
        data = []
        for r in rows:
            marker = "*" if not r["data_romaneio"] else " "
            data.append([
                marker + str(r["id"]),
                r["safra"],
                r["placa"] or "—",
                r["data_saida"] or "—",
                f"{r['volume_m3']}m³" if r["volume_m3"] else "",
                r["codigo_romaneio"] or "",
                r["data_recebimento"] or "",
                _fmt(r["valor_recebido"]),
                f"R${r['preco_m3']:,.2f}/m³" if r["preco_m3"] else "",
                r["observacao"] or "",
            ])

        h, w = stdscr.getmaxyx()
        # Rodapé com ações
        footer = " N=Nova Saída  R=Romaneio  P=Recebimento  Enter=Editar  Esc=Voltar"
        idx = table_view(stdscr, data,
                         ["ID","Safra","Placa","Saída","Volume","Romaneio","Recebimento","Valor","Preço/m³","Obs"],
                         title=" Cargas de Carvão (* = sem romaneio) ",
                         col_widths=[6,7,9,12,9,10,14,11,13,14],
                         footer=footer)

        if idx == -99:   # tecla N
            _registrar_saida(stdscr)
        elif idx == -98:  # tecla R
            _registrar_romaneio(stdscr, rows)
        elif idx == -97:  # tecla P
            _registrar_recebimento(stdscr, rows)
        elif idx >= 0:
            _editar_carga_inline(stdscr, rows[idx]["id"])
        else:
            break


def _registrar_saida(stdscr):
    """Registra a saída de uma nova carga."""
    conn = get_db()
    safras = [r["codigo"] for r in conn.execute(
        "SELECT codigo FROM eu_safra ORDER BY codigo DESC").fetchall()]
    conn.close()
    if not safras:
        flash(stdscr, "Cadastre uma safra primeiro.", error=True)
        return
    fields = [
        {"label": "Safra",       "required": True, "options": safras},
        {"label": "Data Saída",  "default": date.today().isoformat(), "required": True},
        {"label": "Placa",       "required": True},
        {"label": "Tipo",        "options": ["Carga Cheia", "Carga Parcial"],
         "default": "Carga Cheia"},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Registrar Saída de Carga ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        safra = conn.execute("SELECT id FROM eu_safra WHERE codigo=?",
                             (result["Safra"],)).fetchone()
        conn.execute("""INSERT INTO eu_carga
            (id_safra, data_saida, placa, tipo_carga, observacao, status)
            VALUES (?,?,?,?,?,?)""",
            (safra["id"],
             result["Data Saída"],
             result["Placa"],
             result["Tipo"],
             result["Obs."] or None,
             "Pendente"))
        conn.commit()
        flash(stdscr, f"Saída registrada: {result['Placa']} em {result['Data Saída']}")
    except Exception as e:
        flash(stdscr, f"Erro: {e}", error=True)
    finally:
        conn.close()


def _registrar_romaneio(stdscr, rows):
    """Registra ou edita romaneio. Sem romaneio aparecem primeiro (*)."""
    sem = [r for r in rows if not r["data_romaneio"]]
    com = [r for r in rows if r["data_romaneio"]]
    opcoes = (
        [f"* #{r['id']}  {r['placa'] or '—'}  Saída:{r['data_saida'] or '—'}" for r in sem] +
        [f"  #{r['id']}  {r['placa'] or '—'}  Rom:{r['codigo_romaneio'] or '—'}  {r['volume_m3']}m³" for r in com]
    )
    todas = sem + com
    if not opcoes:
        flash(stdscr, "Nenhuma carga registrada.")
        return
    idx = option_picker(stdscr, opcoes, "Selecionar Carga — * sem romaneio", 4, 4)
    if idx is None:
        return
    carga = todas[idx]
    fields = [
        {"label": "Nome do Cliente",    "required": True,
         "default": carga["nome_cliente"] or ""},
        {"label": "Código do Romaneio", "required": True,
         "default": carga["codigo_romaneio"] or ""},
        {"label": "Data Romaneio",      "default": carga["data_romaneio"] or date.today().isoformat()},
        {"label": "Volume (m³)",        "required": True,
         "default": str(carga["volume_m3"]) if carga["volume_m3"] else ""},
    ]
    result = form(stdscr, fields,
                  title=f" Romaneio — Carga #{carga['id']} {carga['placa'] or ''} ",
                  width=56)
    if result is None:
        return
    try:
        vol = float(result["Volume (m³)"].replace(",", "."))
    except ValueError:
        flash(stdscr, "Volume inválido.", error=True)
        return
    conn = get_db()
    conn.execute("""UPDATE eu_carga SET
        nome_cliente=?, codigo_romaneio=?, data_romaneio=?, volume_m3=?,
        status=CASE WHEN status='Pendente' THEN 'Romaneio' ELSE status END
        WHERE id=?""",
        (result["Nome do Cliente"],
         result["Código do Romaneio"],
         result["Data Romaneio"] or date.today().isoformat(),
         vol, carga["id"]))
    conn.commit()
    conn.close()
    flash(stdscr, f"Romaneio #{result['Código do Romaneio']} registrado: {vol} m³")


def _registrar_recebimento(stdscr, rows):
    """Registra ou edita recebimento de uma carga."""
    sem = [r for r in rows if not r["data_recebimento"] and r["data_romaneio"]]
    com = [r for r in rows if r["data_recebimento"]]
    if not sem and not com:
        flash(stdscr, "Nenhuma carga com romaneio disponível.")
        return
    opcoes = (
        [f"* #{r['id']}  {r['placa'] or '—'}  {r['volume_m3']}m³  Rom:{r['codigo_romaneio'] or '—'}" for r in sem] +
        [f"  #{r['id']}  {r['placa'] or '—'}  {r['volume_m3']}m³  R${r['valor_recebido']:,.0f}" for r in com]
    )
    todas = sem + com
    idx = option_picker(stdscr, opcoes, "Selecionar Carga — * sem recebimento", 4, 4)
    if idx is None:
        return
    carga = todas[idx]
    conn = get_db()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conta_atual = ""
    if carga["id_lancamento"]:
        row = conn.execute("""SELECT c.nome FROM fin_conta c
            JOIN fin_lancamento l ON l.id_conta=c.id
            WHERE l.id=?""", (carga["id_lancamento"],)).fetchone()
        if row: conta_atual = row["nome"]
    conn.close()

    fields = [
        {"label": "Data Recebimento",    "required": True,
         "default": carga["data_recebimento"] or date.today().isoformat()},
        {"label": "Valor Recebido (R$)", "required": True,
         "default": str(carga["valor_recebido"]) if carga["valor_recebido"] else ""},
        {"label": "% Acordado",          "required": True,
         "default": str(carga["percentual_recebido"]) if carga["percentual_recebido"] else ""},
        {"label": "Desconto (R$)",
         "default": str(carga["desconto"]) if carga["desconto"] else ""},
        {"label": "Conta",               "options": contas,
         "default": conta_atual or (contas[0] if contas else ""), "required": True},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields,
                  title=f" Recebimento — Carga #{carga['id']} {carga['volume_m3']}m³ ",
                  width=56)
    if result is None:
        return
    try:
        valor_rec = float(result["Valor Recebido (R$)"].replace(",", "."))
        pct       = float(result["% Acordado"].replace(",", "."))
        desc_s    = result["Desconto (R$)"].replace(",", ".")
        desconto  = float(desc_s) if desc_s else None
        vol       = carga["volume_m3"] or 0
        # valor_total = valor bruto a 100% (não afetado pelo desconto)
        valor_total = round(valor_rec / (pct / 100), 2) if pct else valor_rec
        # preco_m3 baseado no valor_total bruto
        preco_m3  = round(valor_total / vol, 2) if vol else None
        # valor que vai para o lançamento = valor_rec - desconto
        valor_lanc = round(valor_rec - (desconto or 0), 2)
    except (ValueError, ZeroDivisionError):
        flash(stdscr, "Valor ou percentual inválido.", error=True)
        return

    conn = get_db()
    id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                            (result["Conta"],)).fetchone()

    if carga["id_lancamento"]:
        # Atualiza lançamento existente com valor líquido
        conn.execute("""UPDATE fin_lancamento SET valor=?, data=?, id_conta=?
            WHERE id=?""",
            (valor_lanc,
             result["Data Recebimento"],
             id_conta["id"] if id_conta else None,
             carga["id_lancamento"]))
        lid = carga["id_lancamento"]
    else:
        # Cria novo lançamento com valor líquido
        lid = criar_lancamento(
            conn, tipo="Receita", valor=valor_lanc,
            descricao=f"Carvão — Carga #{carga['id']} Rom:{carga['codigo_romaneio'] or '—'} {vol}m³",
            categoria="Eucalipto",
            id_conta=id_conta["id"] if id_conta else None,
            data=result["Data Recebimento"],
            status="Realizado",
            origem="eu_carga", id_origem=carga["id"],
        )

    conn.execute("""UPDATE eu_carga SET
        valor_recebido=?, percentual_recebido=?, desconto=?,
        valor_total=?, preco_m3=?,
        data_recebimento=?, id_conta=?, id_lancamento=?, status='Recebida'
        WHERE id=?""",
        (valor_rec, pct, desconto, valor_total, preco_m3,
         result["Data Recebimento"],
         id_conta["id"] if id_conta else None,
         lid, carga["id"]))
    conn.commit()
    conn.close()
    desc_txt = f" − R${desconto:,.2f} desc." if desconto else ""
    flash(stdscr,
          f"Recebido R${valor_rec:,.2f} ({pct}%){desc_txt} → Líq. R${valor_lanc:,.2f}"
          f" | Total bruto R${valor_total:,.2f} | R${preco_m3:,.2f}/m³ | Lanç.#{lid}")


def _editar_carga_inline(stdscr, carga_id):
    """Edita qualquer campo de uma carga. Inclui botão Apagar."""
    conn = get_db()
    c = conn.execute("""
        SELECT c.*, s.codigo as safra_codigo
        FROM eu_carga c JOIN eu_safra s ON c.id_safra=s.id
        WHERE c.id=?
    """, (carga_id,)).fetchone()
    safras = [r["codigo"] for r in conn.execute(
        "SELECT codigo FROM eu_safra ORDER BY codigo DESC").fetchall()]
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not c:
        flash(stdscr, f"Carga #{carga_id} não encontrada.", error=True)
        return

    # Compatibilidade com bancos antigos
    def _safe(key, default=None):
        try: return c[key]
        except IndexError: return default

    conta_nome = ""
    if _safe("id_conta"):
        conn2 = get_db()
        row = conn2.execute("SELECT nome FROM fin_conta WHERE id=?",
                            (_safe("id_conta"),)).fetchone()
        conn2.close()
        if row: conta_nome = row["nome"]

    fields = [
        # ── Saída ──
        {"label": "Safra",           "options": safras,
         "default": c["safra_codigo"]},
        {"label": "Data Saída",      "default": _safe("data_saida") or ""},
        {"label": "Placa",           "default": _safe("placa") or ""},
        {"label": "Tipo",            "options": ["Carga Cheia","Carga Parcial"],
         "default": _safe("tipo_carga") or "Carga Cheia"},
        # ── Romaneio ──
        {"label": "Nome Cliente",    "default": _safe("nome_cliente") or ""},
        {"label": "Cód. Romaneio",   "default": _safe("codigo_romaneio") or ""},
        {"label": "Data Romaneio",   "default": _safe("data_romaneio") or ""},
        {"label": "Volume (m³)",     "default": str(_safe("volume_m3")) if _safe("volume_m3") else ""},
        # ── Recebimento ──
        {"label": "Data Recebimento","default": _safe("data_recebimento") or ""},
        {"label": "Valor Recebido",  "default": str(_safe("valor_recebido")) if _safe("valor_recebido") else ""},
        {"label": "% Acordado",      "default": str(_safe("percentual_recebido")) if _safe("percentual_recebido") else ""},
        {"label": "Desconto (R$)",   "default": str(_safe("desconto")) if _safe("desconto") else ""},
        {"label": "Conta",           "options": [""] + contas, "default": conta_nome},
        {"label": "Obs.",            "default": _safe("observacao") or ""},
        {"label": "⚠ APAGAR",        "options": ["Não","Sim — apagar"], "default": "Não"},
    ]
    result = form(stdscr, fields, title=f" Editar Carga #{carga_id} ", width=58)
    if result is None:
        return

    # Apagar
    if result["⚠ APAGAR"] == "Sim — apagar":
        h, w = stdscr.getmaxyx()
        lid = _safe("id_lancamento")
        aviso = " + lançamento financeiro" if lid else ""
        if not confirm(stdscr, f"Apagar carga #{carga_id}{aviso}?",
                       h//2, max(2, w//2-20)):
            return
        conn = get_db()
        if lid:
            conn.execute("DELETE FROM fin_lancamento WHERE id=?", (lid,))
        conn.execute("DELETE FROM eu_carga WHERE id=?", (carga_id,))
        conn.commit()
        conn.close()
        flash(stdscr, f"Carga #{carga_id} apagada.")
        return

    # Salvar
    conn = get_db()
    try:
        safra = conn.execute("SELECT id FROM eu_safra WHERE codigo=?",
                             (result["Safra"],)).fetchone()
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone() if result["Conta"] else None
        vol_s   = result["Volume (m³)"].replace(",",".")
        vr_s    = result["Valor Recebido"].replace(",",".")
        pct_s   = result["% Acordado"].replace(",",".")
        desc_s  = result["Desconto (R$)"].replace(",",".")
        vol       = float(vol_s)  if vol_s  else None
        valor_rec = float(vr_s)   if vr_s   else None
        pct       = float(pct_s)  if pct_s  else None
        desconto  = float(desc_s) if desc_s else None

        # valor_total e preco_m3: baseados no valor bruto (sem desconto)
        if valor_rec and pct:
            valor_total = round(valor_rec / (pct / 100), 2)
            preco_m3    = round(valor_total / vol, 2) if vol else None
        else:
            valor_total = _safe("valor_total")
            preco_m3    = _safe("preco_m3")
        # Valor que vai para o lançamento = valor_rec - desconto
        valor_lanc = round(valor_rec - (desconto or 0), 2) if valor_rec else None

        # Determina status
        if result["Data Recebimento"]:
            status = "Recebida"
        elif result["Data Romaneio"]:
            status = "Romaneio"
        else:
            status = "Pendente"

        conn.execute("""UPDATE eu_carga SET
            id_safra=?, data_saida=?, placa=?, tipo_carga=?,
            nome_cliente=?, codigo_romaneio=?, data_romaneio=?, volume_m3=?,
            data_recebimento=?, valor_recebido=?, percentual_recebido=?,
            desconto=?, valor_total=?, preco_m3=?, id_conta=?, observacao=?, status=?
            WHERE id=?""",
            (safra["id"] if safra else c["id_safra"],
             result["Data Saída"] or None,
             result["Placa"] or None,
             result["Tipo"],
             result["Nome Cliente"] or None,
             result["Cód. Romaneio"] or None,
             result["Data Romaneio"] or None,
             vol,
             result["Data Recebimento"] or None,
             valor_rec, pct, desconto, valor_total, preco_m3,
             id_conta["id"] if id_conta else None,
             result["Obs."] or None,
             status,
             carga_id))

        # Sync lançamento — usa valor_lanc (valor_rec - desconto)
        lid = _safe("id_lancamento")
        if lid and valor_lanc:
            conn.execute("""UPDATE fin_lancamento SET valor=?, data=?, id_conta=?
                WHERE id=?""",
                (valor_lanc,
                 result["Data Recebimento"] or None,
                 id_conta["id"] if id_conta else None,
                 lid))
        elif not lid and status == "Recebida" and valor_lanc and id_conta:
            lid = criar_lancamento(
                conn, tipo="Receita", valor=valor_lanc,
                descricao=f"Carvão — Carga #{carga_id} Rom:{result['Cód. Romaneio'] or '—'}",
                categoria="Eucalipto",
                id_conta=id_conta["id"],
                data=result["Data Recebimento"] or date.today().isoformat(),
                status="Realizado",
                origem="eu_carga", id_origem=carga_id,
            )
            conn.execute("UPDATE eu_carga SET id_lancamento=? WHERE id=?",
                         (lid, carga_id))

        conn.commit()
        flash(stdscr, f"Carga #{carga_id} atualizada.")
    except (ValueError, ZeroDivisionError) as e:
        flash(stdscr, f"Erro: {e}", error=True)
    finally:
        conn.close()

def screen_despesas_safra(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Despesas"),
            ("➕", "Nova Despesa"),
            ("✏️ ", "Editar Despesa"),
            ("🗑️ ", "Apagar Despesa"),
            ("⬅️ ", "Voltar"),
        ], title=" Despesas de Safra ", y_off=3, x_off=4, width=32)
        if idx == 0: listar_despesas_safra(stdscr)
        elif idx == 1: nova_despesa_safra(stdscr)
        elif idx == 2: editar_despesa_safra(stdscr)
        elif idx == 3: apagar_despesa_safra(stdscr)
        elif idx in (-1, 4): break


def listar_despesas_safra(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT d.id, s.codigo as safra, d.data, d.categoria,
               d.descricao, d.fornecedor, d.valor, d.status,
               c.nome as conta, d.id_lancamento,
               d.data_pagamento, d.observacao
        FROM eu_despesa_safra d
        JOIN eu_safra s ON d.id_safra = s.id
        LEFT JOIN fin_conta c ON d.id_conta = c.id
        ORDER BY d.data DESC, d.id DESC LIMIT 200
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma despesa registrada.")
        return
    data = [[r["id"], r["safra"], r["data"], r["categoria"],
             r["descricao"][:28],
             f"R$ {r['valor']:,.2f}", r["status"]] for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Safra","Data","Categoria","Descrição","Valor","Status"],
                     title=" Despesas de Safra ",
                     col_widths=[5,8,12,15,30,13,10])
    if idx >= 0:
        r = rows[idx]
        pairs = [
            ("ID",          r["id"]),
            ("Safra",       r["safra"]),
            ("Data",        r["data"]),
            ("Categoria",   r["categoria"]),
            ("Descrição",   r["descricao"]),
            ("Fornecedor",  r["fornecedor"] or "—"),
            ("Valor",       f"R$ {r['valor']:,.2f}"),
            ("Status",      r["status"]),
            ("Conta",       r["conta"] or "—"),
            ("Pagamento",   r["data_pagamento"] or "—"),
            ("Lançamento",  f"#{r['id_lancamento']}" if r["id_lancamento"] else "—"),
            ("Obs.",        r["observacao"] or "—"),
        ]
        detail_view(stdscr, pairs, title=f" Despesa #{r['id']} ")


def nova_despesa_safra(stdscr):
    conn = get_db()
    safras = [r["codigo"] for r in conn.execute(
        "SELECT codigo FROM eu_safra ORDER BY codigo DESC").fetchall()]
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not safras:
        flash(stdscr, "Cadastre uma safra primeiro.", error=True)
        return
    fields = [
        {"label": "Safra",      "required": True, "options": safras},
        {"label": "Categoria",  "required": True,
         "options": ["Mão de Obra","Insumos","Equipamentos"]},
        {"label": "Descrição",  "required": True},
        {"label": "Fornecedor"},
        {"label": "Valor (R$)", "required": True},
        {"label": "Data",       "default": date.today().isoformat()},
        {"label": "Status",     "options": ["Realizado","Previsto"], "default": "Realizado"},
        {"label": "Pagamento",  "default": ""},
        {"label": "Conta",      "options": [""] + contas, "default": ""},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nova Despesa de Safra ", width=56)
    if result is None:
        return
    conn = get_db()
    try:
        valor = float(result["Valor (R$)"].replace(",","."))
        safra = conn.execute("SELECT id FROM eu_safra WHERE codigo=?",
                             (result["Safra"],)).fetchone()
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone() if result["Conta"] else None
        data = result["Data"] or date.today().isoformat()
        status = result["Status"]
        # Lançamento financeiro
        lid = criar_lancamento(
            conn, tipo="Despesa", valor=valor,
            descricao=f"Eucalipto safra {result['Safra']} — {result['Categoria']}: {result['Descrição']}",
            categoria="Eucalipto",
            id_conta=id_conta["id"] if id_conta else None,
            data=data,
            data_pagamento=result["Pagamento"] or None,
            status=status,
            origem="eu_despesa_safra",
        )
        cur = conn.execute("""INSERT INTO eu_despesa_safra
            (id_safra, data, categoria, descricao, fornecedor, valor,
             id_conta, data_pagamento, status, id_lancamento, observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (safra["id"], data, result["Categoria"], result["Descrição"],
             result["Fornecedor"] or None,
             valor, id_conta["id"] if id_conta else None,
             result["Pagamento"] or None, status, lid,
             result["Obs."] or None))
        # Update id_origem no lançamento
        conn.execute("UPDATE fin_lancamento SET id_origem=? WHERE id=?",
                     (cur.lastrowid, lid))
        conn.commit()
        flash(stdscr, f"Despesa registrada. Lançamento #{lid}: R$ {valor:,.2f}")
    except ValueError:
        flash(stdscr, "Valor inválido.", error=True)
    finally:
        conn.close()


def editar_despesa_safra(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT d.id, s.codigo as safra, d.id_safra, d.data, d.categoria,
               d.descricao, d.fornecedor, d.valor, d.status, d.id_lancamento,
               d.data_pagamento, d.observacao, c.nome as conta_nome, d.id_conta
        FROM eu_despesa_safra d
        JOIN eu_safra s ON d.id_safra = s.id
        LEFT JOIN fin_conta c ON d.id_conta = c.id
        ORDER BY d.data DESC LIMIT 200
    """).fetchall()
    safras = [r["codigo"] for r in conn.execute(
        "SELECT codigo FROM eu_safra ORDER BY codigo DESC").fetchall()]
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma despesa registrada.")
        return
    data = [[r["id"], r["safra"], r["data"], r["categoria"],
             r["descricao"][:28], f"R$ {r['valor']:,.2f}",
             "✓" if r["id_lancamento"] else "—"] for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Safra","Data","Categoria","Descrição","Valor","Lanç."],
                     title=" Selecionar Despesa para Editar ",
                     col_widths=[5,8,12,15,30,13,6])
    if idx < 0:
        return
    d = rows[idx]
    # Busca status atual do lançamento para pré-preencher
    status_atual = "Realizado"
    if d["id_lancamento"]:
        conn = get_db()
        row = conn.execute("SELECT status FROM fin_lancamento WHERE id=?",
                           (d["id_lancamento"],)).fetchone()
        conn.close()
        status_atual = row["status"] if row else "Realizado"
    fields = [
        {"label": "Safra",      "default": d["safra"],       "options": safras},
        {"label": "Categoria",  "default": d["categoria"],
         "options": ["Mão de Obra","Insumos","Equipamentos"]},
        {"label": "Descrição",  "default": d["descricao"],        "required": True},
        {"label": "Fornecedor", "default": d["fornecedor"] or ""},
        {"label": "Valor (R$)", "default": str(d["valor"]),       "required": True},
        {"label": "Data",       "default": d["data"]},
        {"label": "Status",     "default": status_atual,
         "options": ["Realizado","Previsto"]},
        {"label": "Pagamento",  "default": d["data_pagamento"] or ""},
        {"label": "Conta",      "options": [""] + contas,
         "default": d["conta_nome"] or ""},
        {"label": "Obs.",       "default": d["observacao"] or ""},
    ]
    result = form(stdscr, fields, title=f" Editar Despesa #{d['id']} ", width=56)
    if result is None:
        return
    conn = get_db()
    try:
        valor = float(result["Valor (R$)"].replace(",","."))
        safra = conn.execute("SELECT id FROM eu_safra WHERE codigo=?",
                             (result["Safra"],)).fetchone()
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone() if result["Conta"] else None
        data = result["Data"] or d["data"]
        status = result["Status"]
        desc_lanc = f"Eucalipto safra {result['Safra']} — {result['Categoria']}: {result['Descrição']}"
        # Atualiza lançamento vinculado se existir
        lid = d["id_lancamento"]
        if lid:
            conn.execute("""UPDATE fin_lancamento
                SET valor=?, descricao=?, id_conta=?, data=?,
                    data_pagamento=?, status=?
                WHERE id=?""",
                (valor, desc_lanc,
                 id_conta["id"] if id_conta else None,
                 data, result["Pagamento"] or None, status, lid))
        elif id_conta:
            # Cria lançamento se agora tiver conta
            lid = criar_lancamento(
                conn, tipo="Despesa", valor=valor,
                descricao=desc_lanc, categoria="Eucalipto",
                id_conta=id_conta["id"],
                data=data, data_pagamento=result["Pagamento"] or None,
                status=status, origem="eu_despesa_safra", id_origem=d["id"],
            )
        # Atualiza despesa
        conn.execute("""UPDATE eu_despesa_safra
            SET id_safra=?, data=?, categoria=?, descricao=?, fornecedor=?,
                valor=?, id_conta=?, data_pagamento=?, status=?,
                id_lancamento=?, observacao=?
            WHERE id=?""",
            (safra["id"] if safra else d["id_safra"],
             data, result["Categoria"], result["Descrição"],
             result["Fornecedor"] or None,
             valor, id_conta["id"] if id_conta else None,
             result["Pagamento"] or None, status, lid,
             result["Obs."] or None, d["id"]))
        conn.commit()
        msg = f"Despesa #{d['id']} atualizada."
        if lid: msg += f" Lançamento #{lid} sincronizado."
        flash(stdscr, msg)
    except ValueError:
        flash(stdscr, "Valor inválido.", error=True)
    finally:
        conn.close()


def apagar_despesa_safra(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT d.id, s.codigo as safra, d.data, d.categoria,
               d.descricao, d.valor, d.id_lancamento
        FROM eu_despesa_safra d
        JOIN eu_safra s ON d.id_safra = s.id
        ORDER BY d.data DESC LIMIT 200
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma despesa registrada.")
        return
    data = [[r["id"], r["safra"], r["data"], r["categoria"],
             r["descricao"][:30], f"R$ {r['valor']:,.2f}"] for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Safra","Data","Categoria","Descrição","Valor"],
                     title=" Apagar Despesa ",
                     col_widths=[5,8,12,15,32,13])
    if idx < 0:
        return
    d = rows[idx]
    h, w = stdscr.getmaxyx()
    aviso = " (lançamento financeiro também será apagado)" if d["id_lancamento"] else ""
    if not confirm(stdscr,
                   f"Apagar despesa #{d['id']} R$ {d['valor']:,.2f}?{aviso}",
                   h//2, max(2, w//2-28)):
        return
    conn = get_db()
    if d["id_lancamento"]:
        conn.execute("DELETE FROM fin_lancamento WHERE id=?", (d["id_lancamento"],))
    conn.execute("DELETE FROM eu_despesa_safra WHERE id=?", (d["id"],))
    conn.commit()
    conn.close()
    flash(stdscr, f"Despesa #{d['id']} apagada." +
          (" Lançamento removido." if d["id_lancamento"] else ""))


# ── Movimentações de Talhão ──────────────────────────
def screen_mov_talhao(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Listar Movimentações"),
            ("➕", "Nova Movimentação"),
            ("⬅️ ", "Voltar"),
        ], title=" Mov. Talhão ", y_off=3, x_off=4, width=30)
        if idx == 0: listar_mov_talhao(stdscr)
        elif idx == 1: nova_mov_talhao(stdscr)
        elif idx in (-1, 2): break

def listar_mov_talhao(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, t.nome as talhao, m.data, m.tipo, m.produto, m.quantidade,
               m.custo, m.responsavel
        FROM eu_mov_talhao m JOIN eu_talhao t ON m.id_talhao=t.id
        ORDER BY m.data DESC LIMIT 100
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma movimentação registrada.")
        return
    data = [[r["id"], r["talhao"], r["data"], r["tipo"], r["produto"] or "—",
             r["quantidade"] or "—",
             f"R$ {r['custo']:,.2f}" if r["custo"] else "—"] for r in rows]
    table_view(stdscr, data,
               ["ID","Talhão","Data","Tipo","Produto","Qtd","Custo"],
               title=" Movimentações Talhão ", col_widths=[5,14,12,13,16,10,12])

def nova_mov_talhao(stdscr):
    conn = get_db()
    talhoes = [r["nome"] for r in conn.execute(
        "SELECT nome FROM eu_talhao ORDER BY nome").fetchall()]
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not talhoes:
        flash(stdscr, "Cadastre um talhão primeiro.", error=True)
        return
    fields = [
        {"label": "Talhão",       "required": True, "options": talhoes},
        {"label": "Tipo",         "required": True,
         "options": ["Adubação","Formicida","Desbrota","Calagem","Herbicida","Outro"]},
        {"label": "Produto"},
        {"label": "Quantidade"},
        {"label": "Custo (R$)"},
        {"label": "Data",         "default": date.today().isoformat()},
        {"label": "Status",       "options": ["Realizado","Previsto"], "default": "Realizado"},
        {"label": "Data Pagto",   "default": ""},
        {"label": "Conta",        "options": [""] + contas, "default": ""},
        {"label": "Responsável"},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nova Movimentação de Talhão ", width=56)
    if result is None:
        return
    conn = get_db()
    talhao = conn.execute("SELECT id FROM eu_talhao WHERE nome=?", (result["Talhão"],)).fetchone()
    id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?", (result["Conta"],)).fetchone() if result["Conta"] else None
    custo = float(result["Custo (R$)"]) if result["Custo (R$)"] else None
    lid = None
    if custo and id_conta:
        lid = criar_lancamento(
            conn, tipo="Despesa", valor=custo,
            descricao=f"Eucalipto - {result['Tipo']} em {result['Talhão']}: {result['Produto'] or ''}",
            categoria="Eucalipto",
            id_conta=id_conta["id"],
            data=result["Data"] or date.today().isoformat(),
            data_pagamento=result["Data Pagto"] or None,
            status=result["Status"],
            origem="eu_mov_talhao",
        )
    conn.execute("""INSERT INTO eu_mov_talhao
        (id_talhao, data, tipo, produto, quantidade, custo, id_conta, data_pagamento, id_lancamento, responsavel, observacao)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (talhao["id"], result["Data"] or date.today().isoformat(),
         result["Tipo"], result["Produto"] or None, result["Quantidade"] or None,
         custo, id_conta["id"] if id_conta else None,
         result["Data Pagto"] or None, lid,
         result["Responsável"] or None, result["Obs."] or None))
    conn.commit()
    conn.close()
    msg = f"Movimentação registrada."
    if lid:
        msg += f" Lançamento #{lid} criado."
    flash(stdscr, msg)

# ── Inventário ───────────────────────────────────────
def screen_inventario(stdscr):
    conn = get_db()
    talhoes = conn.execute(
        "SELECT id, nome, area_ha, data_plantio, clone, status FROM eu_talhao ORDER BY nome"
    ).fetchall()
    conn.close()
    if not talhoes:
        flash(stdscr, "Nenhum talhão cadastrado.")
        return
    conn = get_db()
    data = []
    total_vol = 0
    for t in talhoes:
        vol = inventario_talhao(conn, t["id"]) or 0
        total_vol += vol
        # Calcular idade em meses
        idade = "—"
        if t["data_plantio"]:
            try:
                dt = datetime.fromisoformat(t["data_plantio"])
                meses = (date.today().year - dt.year)*12 + (date.today().month - dt.month)
                idade = f"{meses}m"
            except: pass
        data.append([t["nome"], t["area_ha"], t["data_plantio"] or "—",
                     idade, t["clone"] or "—", f"{vol:.1f}", t["status"]])
    data.append(["─"*10,"─"*7,"─"*12,"─"*5,"─"*10,"─"*8,"─"*10])
    data.append(["TOTAL","","","","",f"{total_vol:.1f}",""])
    conn.close()
    table_view(stdscr, data,
               ["Talhão","Área(ha)","Plantio","Idade","Clone","Vol.m³","Status"],
               title=f" Inventário — {date.today().isoformat()} ",
               col_widths=[14,8,12,6,12,9,11])

# ── Curva de Crescimento ─────────────────────────────
def screen_curva(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Ver Curva Atual"),
            ("✏️ ", "Editar Ponto"),
            ("➕", "Adicionar Ponto"),
            ("⬅️ ", "Voltar"),
        ], title=" Curva Crescimento ", y_off=3, x_off=4, width=30)
        if idx == 0: ver_curva(stdscr)
        elif idx == 1: editar_ponto_curva(stdscr)
        elif idx == 2: add_ponto_curva(stdscr)
        elif idx in (-1, 3): break

def ver_curva(stdscr):
    conn = get_db()
    rows = conn.execute(
        "SELECT idade_meses, volume_m3_ha FROM eu_curva_crescimento ORDER BY idade_meses"
    ).fetchall()
    conn.close()
    data = [[r["idade_meses"], f"{r['volume_m3_ha']:.1f}"] for r in rows]
    table_view(stdscr, data, ["Idade (meses)", "Volume (m³/ha)"],
               title=" Curva de Crescimento ", col_widths=[14, 15])

def add_ponto_curva(stdscr):
    fields = [
        {"label": "Idade (meses)", "required": True},
        {"label": "Volume m³/ha",  "required": True},
    ]
    result = form(stdscr, fields, title=" Novo Ponto ", width=44)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("""INSERT INTO eu_curva_crescimento (idade_meses, volume_m3_ha)
            VALUES (?,?) ON CONFLICT(idade_meses) DO UPDATE SET volume_m3_ha=excluded.volume_m3_ha""",
            (int(result["Idade (meses)"]), float(result["Volume m³/ha"])))
        conn.commit()
        flash(stdscr, "Ponto adicionado/atualizado.")
    except ValueError:
        flash(stdscr, "Valores inválidos.", error=True)
    finally:
        conn.close()

def editar_ponto_curva(stdscr):
    conn = get_db()
    rows = conn.execute(
        "SELECT idade_meses, volume_m3_ha FROM eu_curva_crescimento ORDER BY idade_meses"
    ).fetchall()
    conn.close()
    if not rows:
        return
    opcoes = [f"{r['idade_meses']} meses → {r['volume_m3_ha']:.1f} m³/ha" for r in rows]
    idx = option_picker(stdscr, opcoes, "Escolher Ponto", 5, 5)
    if idx is None:
        return
    r = rows[idx]
    fields = [
        {"label": "Idade (meses)", "default": str(r["idade_meses"]), "required": True},
        {"label": "Volume m³/ha",  "default": str(r["volume_m3_ha"]), "required": True},
    ]
    result = form(stdscr, fields, title=" Editar Ponto ", width=44)
    if result is None:
        return
    conn = get_db()
    try:
        conn.execute("DELETE FROM eu_curva_crescimento WHERE idade_meses=?", (r["idade_meses"],))
        conn.execute("INSERT INTO eu_curva_crescimento (idade_meses, volume_m3_ha) VALUES (?,?)",
                     (int(result["Idade (meses)"]), float(result["Volume m³/ha"])))
        conn.commit()
        flash(stdscr, "Ponto atualizado.")
    except ValueError:
        flash(stdscr, "Valores inválidos.", error=True)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════
# MÓDULO: EQUIPAMENTOS
# ═════════════════════════════════════════════════════
def screen_equipamentos(stdscr):
    while True:
        idx = menu(stdscr, [
            ("📋", "Inventário"),
            ("➕", "Cadastrar Equipamento"),
            ("✏️ ", "Editar Equipamento"),
            ("🔧", "Registrar Manutenção"),
            ("✏️ ", "Editar Manutenção"),
            ("📋", "Histórico Manutenções"),
            ("💰", "Registrar Venda"),
            ("⬅️ ", "Voltar"),
        ], title=" Equipamentos ", y_off=3, x_off=4, width=36)
        if idx == 0: inventario_equipamentos(stdscr)
        elif idx == 1: novo_equipamento(stdscr)
        elif idx == 2: editar_equipamento(stdscr)
        elif idx == 3: nova_manutencao(stdscr)
        elif idx == 4: editar_manutencao(stdscr)
        elif idx == 5: historico_manutencoes(stdscr)
        elif idx == 6: vender_equipamento(stdscr)
        elif idx in (-1, 7): break

def inventario_equipamentos(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT e.id, e.nome, e.tipo, e.marca, e.modelo, e.ano,
               e.numero_serie, e.valor_aquisicao, e.data_aquisicao,
               e.status, e.observacao,
               COUNT(m.id) as n_manut,
               COALESCE(SUM(m.custo),0) as custo_manut,
               COALESCE(SUM(CASE WHEN m.subcategoria='Mão de Obra' THEN m.custo ELSE 0 END),0) as custo_mdo,
               COALESCE(SUM(CASE WHEN m.subcategoria='Peças'       THEN m.custo ELSE 0 END),0) as custo_pecas,
               COALESCE(SUM(CASE WHEN m.subcategoria='Insumos'     THEN m.custo ELSE 0 END),0) as custo_ins
        FROM equip_item e
        LEFT JOIN equip_manutencao m ON m.id_equip=e.id
        GROUP BY e.id ORDER BY e.tipo, e.nome
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhum equipamento cadastrado.")
        return
    data = [[r["nome"], r["tipo"], r["marca"] or "—",
             str(r["ano"]) if r["ano"] else "—",
             f"R$ {r['valor_aquisicao']:,.0f}" if r["valor_aquisicao"] else "—",
             r["n_manut"],
             f"R$ {r['custo_manut']:,.0f}",
             r["status"]] for r in rows]
    idx = table_view(stdscr, data,
                     ["Nome","Tipo","Marca","Ano","Aquisição","Manutenções","Custo Mnt.","Status"],
                     title=" Equipamentos ", col_widths=[16,11,10,5,12,12,12,8])
    if idx >= 0:
        r = rows[idx]
        aquis  = r["valor_aquisicao"] or 0
        total  = aquis + r["custo_manut"]
        pairs = [
            ("Nome",                  r["nome"]),
            ("Tipo",                  r["tipo"]),
            ("Marca",                 r["marca"]),
            ("Modelo",                r["modelo"]),
            ("Ano",                   r["ano"]),
            ("Nº Série",              r["numero_serie"] or "—"),
            ("Status",                r["status"]),
            ("── CUSTOS ──",          ""),
            ("  Aquisição",           f"R$ {aquis:,.2f}" if aquis else "—"),
            ("  Manutenção: Mão de Obra", f"R$ {r['custo_mdo']:,.2f}"),
            ("  Manutenção: Peças",   f"R$ {r['custo_pecas']:,.2f}"),
            ("  Manutenção: Insumos", f"R$ {r['custo_ins']:,.2f}"),
            ("  TOTAL GERAL",         f"R$ {total:,.2f}"),
            ("── OUTROS ──",          ""),
            ("  Data Aquis.",         r["data_aquisicao"]),
            ("  Nº Manutenções",      r["n_manut"]),
            ("  Obs.",                r["observacao"]),
        ]
        detail_view(stdscr, pairs, title=f" {r['nome']} ")

def novo_equipamento(stdscr):
    conn = get_db()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    fields = [
        {"label": "Nome",          "required": True},
        {"label": "Tipo",          "required": True,
         "options": ["Trator","Implemento","Veículo","Outro"]},
        {"label": "Marca"},
        {"label": "Modelo"},
        {"label": "Ano"},
        {"label": "Nº Série",      "required": True},
        {"label": "Valor Aquis."},
        {"label": "Data Aquis.",   "default": date.today().isoformat()},
        {"label": "Conta",         "options": [""] + contas, "default": ""},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Novo Equipamento ", width=56)
    if result is None:
        return
    conn = get_db()
    try:
        valor = float(result["Valor Aquis."]) if result["Valor Aquis."] else None
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone() if result["Conta"] else None
        cur = conn.execute("""INSERT INTO equip_item
            (nome, tipo, marca, modelo, ano, numero_serie, valor_aquisicao, data_aquisicao, id_conta, observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (result["Nome"], result["Tipo"],
             result["Marca"] or None, result["Modelo"] or None,
             int(result["Ano"]) if result["Ano"] else None,
             result["Nº Série"] or None, valor,
             result["Data Aquis."] or None,
             id_conta["id"] if id_conta else None,
             result["Obs."] or None))
        eid = cur.lastrowid
        # Lançamento de aquisição
        if valor and id_conta:
            criar_lancamento(
                conn, tipo="Despesa", valor=valor,
                descricao=f"Aquisição: {result['Nome']}",
                categoria="Equipamento",
                id_conta=id_conta["id"],
                data=result["Data Aquis."] or date.today().isoformat(),
                status="Realizado",
                origem="equip_item", id_origem=eid,
            )
        conn.commit()
        flash(stdscr, f"Equipamento '{result['Nome']}' cadastrado!")
    except ValueError as e:
        flash(stdscr, f"Erro: {e}", error=True)
    finally:
        conn.close()

def nova_manutencao(stdscr):
    conn = get_db()
    equips = conn.execute(
        "SELECT id, nome FROM equip_item WHERE status='Ativo' ORDER BY nome"
    ).fetchall()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not equips:
        flash(stdscr, "Nenhum equipamento ativo.")
        return
    fields = [
        {"label": "Equipamento",   "required": True,
         "options": [r["nome"] for r in equips]},
        {"label": "Tipo",          "required": True,
         "options": ["Preventiva","Corretiva","Revisão"]},
        {"label": "Subcategoria",  "required": True,
         "options": ["Mão de Obra","Peças","Insumos"]},
        {"label": "Descrição"},
        {"label": "Custo (R$)"},
        {"label": "Prestador"},
        {"label": "Data",          "default": date.today().isoformat()},
        {"label": "Status",        "options": ["Realizado","Previsto"], "default": "Realizado"},
        {"label": "Data Pagto",    "default": ""},
        {"label": "Conta",         "options": [""] + contas, "default": ""},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nova Manutenção ", width=56)
    if result is None:
        return
    conn = get_db()
    equip = conn.execute("SELECT id FROM equip_item WHERE nome=?", (result["Equipamento"],)).fetchone()
    id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                            (result["Conta"],)).fetchone() if result["Conta"] else None
    custo = float(result["Custo (R$)"]) if result["Custo (R$)"] else None
    lid = None
    if custo and id_conta:
        lid = criar_lancamento(
            conn, tipo="Despesa", valor=custo,
            descricao=f"Manutenção {result['Tipo']} ({result['Subcategoria']}): {result['Equipamento']}",
            categoria="Equipamento",
            id_conta=id_conta["id"],
            data=result["Data"] or date.today().isoformat(),
            data_pagamento=result["Data Pagto"] or None,
            status=result["Status"],
            origem="equip_manutencao",
        )
    conn.execute("""INSERT INTO equip_manutencao
        (id_equip, data, tipo, subcategoria, descricao, custo, prestador, id_conta, data_pagamento, id_lancamento, observacao)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (equip["id"], result["Data"] or date.today().isoformat(),
         result["Tipo"], result["Subcategoria"],
         result["Descrição"] or None, custo,
         result["Prestador"] or None,
         id_conta["id"] if id_conta else None,
         result["Data Pagto"] or None, lid,
         result["Obs."] or None))
    conn.commit()
    conn.close()
    flash(stdscr, f"Manutenção registrada." + (f" Lançamento #{lid} criado." if lid else ""))

def historico_manutencoes(stdscr):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, e.nome as equip, m.data, m.tipo, m.descricao,
               m.custo, m.prestador
        FROM equip_manutencao m JOIN equip_item e ON m.id_equip=e.id
        ORDER BY m.data DESC LIMIT 100
    """).fetchall()
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma manutenção registrada.")
        return
    data = [[r["id"], r["equip"], r["data"], r["tipo"],
             r["descricao"] or "—",
             f"R$ {r['custo']:,.2f}" if r["custo"] else "—",
             r["prestador"] or "—"] for r in rows]
    table_view(stdscr, data,
               ["ID","Equipamento","Data","Tipo","Descrição","Custo","Prestador"],
               title=" Manutenções ", col_widths=[5,16,12,11,18,12,14])

def editar_equipamento(stdscr):
    """Edita dados cadastrais de um equipamento, incluindo data e valor de aquisição."""
    conn = get_db()
    equips = conn.execute(
        "SELECT id, nome FROM equip_item ORDER BY nome"
    ).fetchall()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not equips:
        flash(stdscr, "Nenhum equipamento cadastrado.")
        return
    idx = option_picker(stdscr, [r["nome"] for r in equips], "Escolher Equipamento", 5, 5)
    if idx is None:
        return
    conn = get_db()
    e = conn.execute("SELECT * FROM equip_item WHERE id=?", (equips[idx]["id"],)).fetchone()
    # Busca lançamento de aquisição vinculado
    lanc_aquis = conn.execute("""
        SELECT id, valor, data, id_conta FROM fin_lancamento
        WHERE origem='equip_item' AND id_origem=? AND tipo='Despesa'
        ORDER BY id LIMIT 1""", (e["id"],)).fetchone()
    conta_atual = ""
    if e["id_conta"]:
        row = conn.execute("SELECT nome FROM fin_conta WHERE id=?",
                           (e["id_conta"],)).fetchone()
        conta_atual = row["nome"] if row else ""
    conn.close()

    fields = [
        {"label": "Nome",          "default": e["nome"],              "required": True},
        {"label": "Tipo",          "default": e["tipo"],
         "options": ["Trator","Implemento","Veículo","Outro"]},
        {"label": "Marca",         "default": e["marca"]        or ""},
        {"label": "Modelo",        "default": e["modelo"]       or ""},
        {"label": "Ano",           "default": str(e["ano"])     if e["ano"] else ""},
        {"label": "Nº Série",      "default": e["numero_serie"] or "", "required": True},
        {"label": "Valor Aquis.",  "default": str(e["valor_aquisicao"]) if e["valor_aquisicao"] else ""},
        {"label": "Data Aquis.",   "default": e["data_aquisicao"] or ""},
        {"label": "Status",        "default": e["status"],
         "options": ["Ativo","Vendido","Sucata"]},
        {"label": "Obs.",          "default": e["observacao"]   or ""},
    ]
    result = form(stdscr, fields, title=f" Editar: {e['nome']} ", width=56)
    if result is None:
        return
    conn = get_db()
    try:
        novo_valor = float(result["Valor Aquis."].replace(",",".")) if result["Valor Aquis."] else None
        nova_data  = result["Data Aquis."] or None

        conn.execute("""UPDATE equip_item
            SET nome=?, tipo=?, marca=?, modelo=?, ano=?, numero_serie=?,
                valor_aquisicao=?, data_aquisicao=?, status=?, observacao=?
            WHERE id=?""",
            (result["Nome"], result["Tipo"],
             result["Marca"]  or None,
             result["Modelo"] or None,
             int(result["Ano"]) if result["Ano"] else None,
             result["Nº Série"],
             novo_valor, nova_data,
             result["Status"],
             result["Obs."] or None,
             e["id"]))

        # Atualiza lançamento de aquisição se existir
        if lanc_aquis and novo_valor is not None:
            conn.execute("""UPDATE fin_lancamento
                SET valor=?, data=?, descricao=?
                WHERE id=?""",
                (novo_valor,
                 nova_data or lanc_aquis["data"],
                 f"Aquisição: {result['Nome']}",
                 lanc_aquis["id"]))

        conn.commit()
        msg = f"Equipamento '{result['Nome']}' atualizado."
        if lanc_aquis and novo_valor is not None:
            msg += " Lançamento de aquisição sincronizado."
        flash(stdscr, msg)
    except ValueError as ex:
        flash(stdscr, f"Erro: {ex}", error=True)
    finally:
        conn.close()


def editar_manutencao(stdscr):
    """
    Edita uma manutenção existente.
    Se houver lançamento financeiro vinculado, atualiza custo, conta, data e status.
    Se não houver lançamento e o usuário preencher custo + conta, cria um novo.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT m.id, e.nome as equip, m.data, m.tipo, m.subcategoria, m.descricao,
               m.custo, m.prestador, m.id_lancamento, m.id_conta,
               m.data_pagamento, m.observacao,
               c.nome as conta_nome,
               l.status as status_edit
        FROM equip_manutencao m
        JOIN equip_item e ON m.id_equip = e.id
        LEFT JOIN fin_conta c ON m.id_conta = c.id
        LEFT JOIN fin_lancamento l ON m.id_lancamento = l.id
        ORDER BY m.data DESC LIMIT 100
    """).fetchall()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not rows:
        flash(stdscr, "Nenhuma manutenção registrada.")
        return
    # Tabela de seleção
    data = [[r["id"], r["equip"], r["data"], r["tipo"],
             f"R$ {r['custo']:,.2f}" if r["custo"] else "—",
             "✓" if r["id_lancamento"] else "—"] for r in rows]
    idx = table_view(stdscr, data,
                     ["ID","Equipamento","Data","Tipo","Custo","Lanç."],
                     title=" Selecionar Manutenção para Editar ",
                     col_widths=[5,18,12,11,12,6])
    if idx < 0:
        return
    m = rows[idx]
    fields = [
        {"label": "Tipo",          "default": m["tipo"],
         "options": ["Preventiva","Corretiva","Revisão"]},
        {"label": "Subcategoria",  "default": m["subcategoria"] or "Mão de Obra",
         "options": ["Mão de Obra","Peças","Insumos"]},
        {"label": "Descrição",     "default": m["descricao"]    or ""},
        {"label": "Custo (R$)",    "default": str(m["custo"])   if m["custo"] else ""},
        {"label": "Prestador",     "default": m["prestador"]    or ""},
        {"label": "Data",          "default": m["data"]},
        {"label": "Status",        "options": ["Realizado","Previsto"],
         "default": m["status_edit"] or "Realizado"},
        {"label": "Data Pagto",    "default": m["data_pagamento"] or ""},
        {"label": "Conta",         "options": [""] + contas,
         "default": m["conta_nome"] or ""},
        {"label": "Obs.",          "default": m["observacao"]   or ""},
    ]
    result = form(stdscr, fields, title=f" Editar Manutenção #{m['id']} ", width=56)
    if result is None:
        return
    conn = get_db()
    try:
        novo_custo = float(result["Custo (R$)"]) if result["Custo (R$)"] else None
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone() if result["Conta"] else None
        novo_status = result["Status"]

        # ── Atualiza ou cria lançamento financeiro ──────────
        lid = m["id_lancamento"]
        if lid:
            # Lançamento existe — atualiza todos os campos relevantes
            conn.execute("""UPDATE fin_lancamento
                SET valor=?, id_conta=?, data=?, data_pagamento=?,
                    status=?, descricao=?
                WHERE id=?""",
                (novo_custo or 0,
                 id_conta["id"] if id_conta else None,
                 result["Data"] or m["data"],
                 result["Data Pagto"] or None,
                 novo_status,
                 f"Manutenção {result['Tipo']}: {m['equip']}",
                 lid))
        elif novo_custo and id_conta:
            # Sem lançamento anterior — cria um novo se custo e conta preenchidos
            lid = criar_lancamento(
                conn, tipo="Despesa", valor=novo_custo,
                descricao=f"Manutenção {result['Tipo']}: {m['equip']}",
                categoria="Equipamento",
                id_conta=id_conta["id"],
                data=result["Data"] or m["data"],
                data_pagamento=result["Data Pagto"] or None,
                status=novo_status,
                origem="equip_manutencao", id_origem=m["id"],
            )

        # ── Atualiza a manutenção ────────────────────────────
        conn.execute("""UPDATE equip_manutencao
            SET tipo=?, subcategoria=?, descricao=?, custo=?, prestador=?,
                data=?, data_pagamento=?, id_conta=?,
                id_lancamento=?, observacao=?
            WHERE id=?""",
            (result["Tipo"],
             result["Subcategoria"],
             result["Descrição"] or None,
             novo_custo,
             result["Prestador"] or None,
             result["Data"] or m["data"],
             result["Data Pagto"] or None,
             id_conta["id"] if id_conta else None,
             lid,
             result["Obs."] or None,
             m["id"]))
        conn.commit()

        msg = f"Manutenção #{m['id']} atualizada."
        if lid == m["id_lancamento"] and lid:
            msg += f" Lançamento #{lid} sincronizado."
        elif lid and not m["id_lancamento"]:
            msg += f" Lançamento #{lid} criado."
        flash(stdscr, msg)
    except ValueError as ex:
        flash(stdscr, f"Erro: {ex}", error=True)
    finally:
        conn.close()


def vender_equipamento(stdscr):
    conn = get_db()
    equips = conn.execute(
        "SELECT id, nome FROM equip_item WHERE status='Ativo' ORDER BY nome"
    ).fetchall()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not equips:
        flash(stdscr, "Nenhum equipamento ativo.")
        return
    idx = option_picker(stdscr, [r["nome"] for r in equips], "Selecionar Equipamento", 5, 5)
    if idx is None:
        return
    equip = equips[idx]
    fields = [
        {"label": "Valor Venda",  "required": True},
        {"label": "Data Venda",   "default": date.today().isoformat()},
        {"label": "Conta",        "options": contas, "default": contas[0] if contas else ""},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=f" Vender: {equip['nome']} ", width=52)
    if result is None:
        return
    conn = get_db()
    try:
        valor = float(result["Valor Venda"])
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?",
                                (result["Conta"],)).fetchone()
        criar_lancamento(
            conn, tipo="Receita", valor=valor,
            descricao=f"Venda equipamento: {equip['nome']}",
            categoria="Equipamento",
            id_conta=id_conta["id"] if id_conta else None,
            data=result["Data Venda"],
            status="Realizado",
            origem="equip_item", id_origem=equip["id"],
        )
        conn.execute("UPDATE equip_item SET status='Vendido' WHERE id=?", (equip["id"],))
        conn.commit()
        flash(stdscr, f"{equip['nome']} vendido por R$ {valor:,.2f}. Lançamento criado.")
    except ValueError:
        flash(stdscr, "Valor inválido.", error=True)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════
# DASHBOARD CONSOLIDADO
# ═════════════════════════════════════════════════════
def screen_dashboard(stdscr):
    conn = get_db()
    # Gado
    total_gado = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo'").fetchone()[0]
    prenhas    = conn.execute("SELECT COUNT(*) FROM reproducao WHERE resultado_dg='Positivo' AND data_parto_real IS NULL").fetchone()[0]
    # Eucalipto
    talhoes_ativos = conn.execute("SELECT COUNT(*) FROM eu_talhao WHERE status='Crescendo'").fetchone()[0]
    cargas_pend    = conn.execute("SELECT COUNT(*) FROM eu_carga WHERE status IN ('Pendente','Romaneio')").fetchone()[0]
    vol_total      = sum(inventario_talhao(conn, r["id"]) or 0
                        for r in conn.execute("SELECT id FROM eu_talhao WHERE status='Crescendo'").fetchall())
    # Financeiro
    ano_atual = str(date.today().year)
    rec_ano = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
        WHERE tipo='Receita' AND status='Realizado' AND strftime('%Y',data)=?""", (ano_atual,)).fetchone()[0]
    des_ano = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
        WHERE tipo='Despesa' AND status='Realizado' AND strftime('%Y',data)=?""", (ano_atual,)).fetchone()[0]
    contas = conn.execute("""
        SELECT c.nome,
               c.saldo_inicial +
               COALESCE(SUM(CASE WHEN l.tipo='Receita' AND l.status='Realizado' THEN l.valor ELSE 0 END),0) -
               COALESCE(SUM(CASE WHEN l.tipo='Despesa' AND l.status='Realizado' THEN l.valor ELSE 0 END),0) AS saldo
        FROM fin_conta c LEFT JOIN fin_lancamento l ON l.id_conta=c.id
        WHERE c.ativa=1 GROUP BY c.id ORDER BY c.nome
    """).fetchall()
    # Equipamentos
    equips_ativos = conn.execute("SELECT COUNT(*) FROM equip_item WHERE status='Ativo'").fetchone()[0]
    ult_pesagens  = conn.execute("""
        SELECT a.brinco, p.peso_kg, p.data_pesagem FROM pesagem p
        JOIN animal a ON p.id_animal=a.id ORDER BY p.data_pesagem DESC, p.id DESC LIMIT 5
    """).fetchall()
    conn.close()

    h, w = stdscr.getmaxyx()
    stdscr.erase()
    draw_header(stdscr, "🏡  FAZENDA — Gestão Rural")
    draw_footer(stdscr, "Q/Enter voltar ao menu")

    y = 2
    # ── KPIs linha 1: Gado + Eucalipto ──────────────
    safe_addstr(stdscr, y, 2, " GADO ", HEADER())
    safe_addstr(stdscr, y, 10, f"Rebanho: {total_gado}   Prenhas: {prenhas}", INFO())
    y += 1
    safe_addstr(stdscr, y, 2, " EUCALIPTO ", HEADER())
    safe_addstr(stdscr, y, 14, f"Talhões crescendo: {talhoes_ativos}   Vol. estimado: {vol_total:.0f} m³   Cargas pendentes: {cargas_pend}", INFO())
    y += 1
    safe_addstr(stdscr, y, 2, " EQUIPAMENTOS ", HEADER())
    safe_addstr(stdscr, y, 17, f"Ativos: {equips_ativos}", INFO())
    y += 1

    # ── Financeiro ───────────────────────────────────
    safe_addstr(stdscr, y, 2, f" FINANCEIRO {ano_atual} ", HEADER())
    saldo_str = f"R$ {rec_ano-des_ano:,.0f}"
    cor = SUCCESS() if rec_ano >= des_ano else ERROR()
    safe_addstr(stdscr, y, 18, f"Receitas: R$ {rec_ano:,.0f}   Despesas: R$ {des_ano:,.0f}   Resultado: ", INFO())
    safe_addstr(stdscr, y, 18 + 56, saldo_str, cor)
    y += 1

    # Saldos por conta
    for c in contas:
        if y >= h - 6: break
        cor = SUCCESS() if c["saldo"] >= 0 else ERROR()
        safe_addstr(stdscr, y, 4, f"  {c['nome']:<20} R$ {c['saldo']:>12,.2f}", cor)
        y += 1

    y += 1
    # ── Últimas pesagens ─────────────────────────────
    if ult_pesagens and y < h - 6:
        safe_addstr(stdscr, y, 2, " Últimas Pesagens ", HEADER())
        y += 1
        for p in ult_pesagens:
            if y >= h - 3: break
            safe_addstr(stdscr, y, 4,
                        f"{p['brinco']:<8}  {p['peso_kg']:>6.1f} kg   {p['data_pesagem']}",
                        NORMAL())
            y += 1

    stdscr.refresh()
    while True:
        key = stdscr.getch()
        if key in (ord("q"), ord("Q"), 27, curses.KEY_ENTER, 10, 13):
            break


def draw_dashboard(stdscr):
    """Fundo resumido atrás do menu principal."""
    h, w = stdscr.getmaxyx()
    draw_header(stdscr, "🏡  FAZENDA — Gestão Rural")
    conn = get_db()
    total  = conn.execute("SELECT COUNT(*) FROM animal WHERE status='Ativo'").fetchone()[0]
    rec    = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
        WHERE tipo='Receita' AND status='Realizado' AND strftime('%Y',data)=?""",
        (str(date.today().year),)).fetchone()[0]
    des    = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
        WHERE tipo='Despesa' AND status='Realizado' AND strftime('%Y',data)=?""",
        (str(date.today().year),)).fetchone()[0]
    cargas = conn.execute("SELECT COUNT(*) FROM eu_carga WHERE status IN ('Pendente','Romaneio')").fetchone()[0]
    conn.close()

    safe_addstr(stdscr, 2, 2, "Gado: ", TITLE())
    safe_addstr(stdscr, 2, 8, str(total) + " ativos", INFO())
    safe_addstr(stdscr, 2, 22, "Resultado " + str(date.today().year) + ": ", TITLE())
    cor = SUCCESS() if rec >= des else ERROR()
    safe_addstr(stdscr, 2, 38, f"R$ {rec-des:,.0f}", cor)
    safe_addstr(stdscr, 2, 52, "Cargas pendentes: ", TITLE())
    safe_addstr(stdscr, 2, 70, str(cargas), WARN() if cargas > 0 else INFO())
    stdscr.refresh()


# ═════════════════════════════════════════════════════
# MENU PRINCIPAL
# ═════════════════════════════════════════════════════
def main_loop(stdscr):
    C.init()
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(-1)

    MENU_ITEMS = [
        ("🏠", "Dashboard"),
        ("🐄", "Gado"),
        ("🌲", "Eucalipto"),
        ("💰", "Financeiro"),
        ("🔧", "Equipamentos"),
        ("📊", "Relatórios"),
        ("🚪", "Sair"),
    ]

    while True:
        stdscr.erase()
        draw_dashboard(stdscr)
        draw_footer(stdscr)

        h, w = stdscr.getmaxyx()
        idx = menu(stdscr, MENU_ITEMS,
                   title=" Menu Principal ",
                   y_off=h // 2 - len(MENU_ITEMS) // 2 - 2,
                   x_off=w // 2 - 18,
                   width=36)

        if idx == 0:
            screen_dashboard(stdscr)
        elif idx == 1:
            screen_gado(stdscr)
        elif idx == 2:
            screen_eucalipto(stdscr)
        elif idx == 3:
            screen_financeiro(stdscr)
        elif idx == 4:
            screen_equipamentos(stdscr)
        elif idx == 5:
            screen_relatorios_fazenda(stdscr)
        elif idx in (6, -1):
            break


def screen_gado(stdscr):
    """Submenu de gado."""
    while True:
        idx = menu(stdscr, [
            ("🐄", "Animais"),
            ("🛒", "Compra de Animais"),
            ("🍼", "Nascimento"),
            ("⚖️ ", "Pesagem"),
            ("📦", "Lotes"),
            ("🌿", "Pastos"),
            ("❤️ ", "Reprodução"),
            ("🛡️ ", "Sanidade"),
            ("💰", "Movimentações/Vendas"),
            ("⬅️ ", "Voltar"),
        ], title=" Gado ", y_off=3, x_off=4, width=36)
        if idx == 0: screen_animais(stdscr)
        elif idx == 1: compra_animais(stdscr)
        elif idx == 2: registrar_nascimento(stdscr)
        elif idx == 3: screen_pesagem(stdscr)
        elif idx == 4: screen_lotes(stdscr)
        elif idx == 5: screen_pastos(stdscr)
        elif idx == 6: screen_reproducao(stdscr)
        elif idx == 7: screen_sanidade(stdscr)
        elif idx == 8: screen_movimentacoes(stdscr)
        elif idx in (-1, 9): break


def screen_relatorios_fazenda(stdscr):
    """Relatórios consolidados da fazenda."""
    while True:
        idx = menu(stdscr, [
            ("🐄", "Resultado Gado (Anual)"),
            ("🌲", "Resultado Eucalipto por Safra"),
            ("📊", "Resultado Consolidado (Anual)"),
            ("⚖️ ", "GMD por Animal"),
            ("❤️ ", "Indicadores Reprodutivos"),
            ("⬅️ ", "Voltar"),
        ], title=" Relatórios ", y_off=3, x_off=4, width=40)
        if idx == 0: _relatorio_unidade(stdscr, "Gado")
        elif idx == 1: _relatorio_safra_eucalipto(stdscr)
        elif idx == 2: resultado_anual(stdscr)
        elif idx == 3: relatorio_gmd(stdscr)
        elif idx == 4: relatorio_prenhez(stdscr)
        elif idx in (-1, 5): break


def _relatorio_unidade(stdscr, categoria):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 30, h//2-2, w//2-15)
    win.erase(); draw_box(win, f" Relatório {categoria} ")
    safe_addstr(win, 2, 2, "Ano (ex: 2025): ", TITLE())
    win.refresh()
    ano = text_input(win, 2, 18, 8, str(date.today().year))
    if not ano:
        return
    conn = get_db()
    rec = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
        WHERE tipo='Receita' AND categoria=? AND status='Realizado'
        AND strftime('%Y',data)=?""", (categoria, ano)).fetchone()[0]
    des = conn.execute("""SELECT COALESCE(SUM(valor),0) FROM fin_lancamento
        WHERE tipo='Despesa' AND categoria=? AND status='Realizado'
        AND strftime('%Y',data)=?""", (categoria, ano)).fetchone()[0]
    # Detalhes por descrição
    itens = conn.execute("""SELECT tipo, descricao, valor, data FROM fin_lancamento
        WHERE categoria=? AND status='Realizado' AND strftime('%Y',data)=?
        ORDER BY data""", (categoria, ano)).fetchall()
    conn.close()
    pairs = [
        (f"── {categoria.upper()} {ano} ──", ""),
        ("Receitas",  f"R$ {rec:,.2f}"),
        ("Despesas",  f"R$ {des:,.2f}"),
        ("Resultado", f"R$ {rec-des:,.2f}"),
        ("── LANÇAMENTOS ──", ""),
    ]
    for i in itens:
        sinal = "+" if i["tipo"] == "Receita" else "-"
        pairs.append(("  ", f"{i['data']} {sinal}R$ {i['valor']:,.2f}  {i['descricao'][:40]}"))
    detail_view(stdscr, pairs, title=f" {categoria} {ano} ")


def _relatorio_safra_eucalipto(stdscr):
    conn = get_db()
    safras = conn.execute("SELECT id, codigo FROM eu_safra ORDER BY codigo DESC").fetchall()
    conn.close()
    if not safras:
        flash(stdscr, "Nenhuma safra cadastrada.")
        return
    idx = option_picker(stdscr, [r["codigo"] for r in safras], "Escolher Safra", 5, 10)
    if idx is None:
        return
    conn = get_db()
    s = conn.execute("SELECT * FROM eu_safra WHERE id=?", (safras[idx]["id"],)).fetchone()
    # Busca o objeto como Row para passar para _detalhe_safra
    row = conn.execute("""
        SELECT s.id, s.codigo, s.status, s.data_inicio, s.data_fim,
               COUNT(c.id) as n_cargas,
               COALESCE(SUM(c.volume_m3),0) as vol_total,
               COALESCE(SUM(c.valor_total),0) as rec_total
        FROM eu_safra s LEFT JOIN eu_carga c ON c.id_safra=s.id
        WHERE s.id=? GROUP BY s.id
    """, (s["id"],)).fetchone()
    conn.close()
    _detalhe_safra(stdscr, row)



# ═════════════════════════════════════════════════════
# COMPRA DE ANIMAIS
# ═════════════════════════════════════════════════════
def compra_animais(stdscr):
    """
    Fluxo de compra de lote de animais:
    1. Cabecalho: data, vendedor, NF, valor/@, conta, status
    2. Loop de animais: brinco, sexo, categoria, raca, peso ou valor direto
    3. Resumo + confirmacao
    4. Grava animais + movimentacoes individuais + 1 lancamento financeiro total
    """
    h, w = stdscr.getmaxyx()

    conn = get_db()
    contas = [r["nome"] for r in conn.execute(
        "SELECT nome FROM fin_conta WHERE ativa=1 ORDER BY nome").fetchall()]
    conn.close()
    if not contas:
        flash(stdscr, "Cadastre uma conta bancaria antes de registrar compras.", error=True)
        return

    cabecalho_fields = [
        {"label": "Data",          "default": date.today().isoformat()},
        {"label": "Vendedor"},
        {"label": "Nota Fiscal"},
        {"label": "Valor/@ (R$)",  "default": ""},
        {"label": "Conta",         "required": True, "options": contas},
        {"label": "Status",        "options": ["Realizado","Previsto"], "default": "Realizado"},
        {"label": "Obs."},
    ]
    cab = form(stdscr, cabecalho_fields, title=" Compra de Animais - Cabecalho ", width=58)
    if cab is None:
        return

    data_compra  = cab["Data"] or date.today().isoformat()
    vendedor     = cab["Vendedor"] or None
    nota_fiscal  = cab["Nota Fiscal"] or None
    va_str       = cab["Valor/@ (R$)"].replace(",",".") if cab["Valor/@ (R$)"] else ""
    valor_arroba = float(va_str) if va_str else None
    conta_nome   = cab["Conta"]
    status_fin   = cab["Status"]

    animais = []

    while True:
        stdscr.erase()
        draw_header(stdscr, "  Compra de Animais")
        draw_footer(stdscr, "Brinco em branco + SALVAR = finalizar compra")

        total_acum = sum(a["valor_total"] or 0 for a in animais)
        safe_addstr(stdscr, 2, 2,
                    "Vendedor: " + (vendedor or "-") + "   NF: " + (nota_fiscal or "-") + "   Data: " + data_compra,
                    INFO())
        safe_addstr(stdscr, 3, 2,
                    "Animais: " + str(len(animais)) + "   Total: R$ " + f"{total_acum:,.2f}",
                    SUCCESS() if animais else NORMAL())

        if animais:
            safe_addstr(stdscr, 4, 2,
                        ("Brinco  ").ljust(9) + ("Categ.").ljust(11) + ("Peso").rjust(8) + ("  Valor").rjust(12),
                        HEADER())
            for i, a in enumerate(animais[-8:]):
                val_str  = "R$ " + f"{a['valor_total']:,.2f}" if a["valor_total"] else "-"
                peso_str = f"{a['peso_kg']:.1f} kg" if a["peso_kg"] else "-"
                safe_addstr(stdscr, 5 + i, 2,
                            a["brinco"].ljust(9) + a["categoria"].ljust(11) + peso_str.rjust(8) + ("  " + val_str).rjust(12),
                            NORMAL())
        stdscr.refresh()

        last_cat = animais[-1]["categoria"] if animais else "Novilho"
        last_sexo = animais[-1]["sexo"] if animais else "M"
        last_raca = animais[-1]["raca"] if animais else ""
        animal_fields = [
            {"label": "Brinco"},
            {"label": "Sexo",              "options": ["M","F"], "default": last_sexo},
            {"label": "Categoria",         "options": ["Bezerro","Bezerra","Novilho","Novilha","Vaca","Touro","Boi"],
             "default": last_cat},
            {"label": "Raca",              "default": last_raca},
            {"label": "Modo valor",        "options": ["Peso + arroba","Valor direto"], "default": "Peso + arroba"},
            {"label": "Peso (kg)",         "default": ""},
            {"label": "Valor total (R$)",  "default": ""},
        ]
        row_y = min(max(5 + min(len(animais), 8) + 2, 14), h - 16)
        res = form(stdscr, animal_fields,
                   title=" Proximo Animal (brinco vazio = finalizar) ",
                   width=54, y_off=row_y)

        if res is None:
            if animais:
                if confirm(stdscr, "Cancelar compra? Nenhum animal sera gravado.", h//2, max(2, w//2-22)):
                    return
            else:
                return
            continue

        if not res["Brinco"].strip():
            if not animais:
                flash(stdscr, "Nenhum animal adicionado.", error=True)
                continue
            break

        if any(a["brinco"] == res["Brinco"].strip() for a in animais):
            flash(stdscr, "Brinco " + res["Brinco"] + " ja adicionado nesta compra.", error=True)
            continue

        try:
            modo = res["Modo valor"]
            peso_s = res["Peso (kg)"].replace(",",".") if res["Peso (kg)"] else ""
            val_s  = res["Valor total (R$)"].replace(",",".") if res["Valor total (R$)"] else ""
            peso   = float(peso_s) if peso_s else None
            val_d  = float(val_s)  if val_s  else None

            if modo == "Peso + arroba":
                if not peso:
                    flash(stdscr, "Informe o peso para o modo Peso + arroba.", error=True)
                    continue
                vt = (peso / 15 * valor_arroba) if valor_arroba else None
            else:
                vt   = val_d
                peso = None

            animais.append({
                "brinco":      res["Brinco"].strip(),
                "sexo":        res["Sexo"],
                "categoria":   res["Categoria"],
                "raca":        res["Raca"] or None,
                "peso_kg":     peso,
                "valor_total": vt,
            })
        except ValueError:
            flash(stdscr, "Valor numerico invalido.", error=True)

    # Resumo e confirmacao
    stdscr.erase()
    draw_header(stdscr, "  Confirmar Compra")
    draw_footer(stdscr, "")
    total_geral = sum(a["valor_total"] or 0 for a in animais)
    safe_addstr(stdscr, 2, 2, "Data: " + data_compra + "  Vendedor: " + (vendedor or "-") + "  NF: " + (nota_fiscal or "-"), INFO())
    safe_addstr(stdscr, 3, 2, "Conta: " + conta_nome + "  Status: " + status_fin, INFO())
    safe_addstr(stdscr, 4, 2,
                ("Brinco").ljust(9) + ("Sx").ljust(4) + ("Cat.").ljust(11) + ("Raca").ljust(11) + ("Peso").rjust(7) + ("  Valor").rjust(12),
                HEADER())
    for i, a in enumerate(animais):
        val_str  = "R$ " + f"{a['valor_total']:,.2f}" if a["valor_total"] else "-"
        peso_str = f"{a['peso_kg']:.1f}" if a["peso_kg"] else "-"
        safe_addstr(stdscr, 5 + i, 2,
                    a["brinco"].ljust(9) + a["sexo"].ljust(4) + a["categoria"].ljust(11) + (a["raca"] or "-").ljust(11) + peso_str.rjust(7) + ("  " + val_str).rjust(12),
                    NORMAL())
    ty = 5 + len(animais) + 1
    safe_addstr(stdscr, ty, 2,
                "TOTAL: " + str(len(animais)) + " animais   R$ " + f"{total_geral:,.2f}",
                SUCCESS())
    stdscr.refresh()

    if not confirm(stdscr, "Confirmar compra de " + str(len(animais)) + " animais?", ty + 2, 4):
        return

    # Gravar
    conn = get_db()
    try:
        id_conta = conn.execute("SELECT id FROM fin_conta WHERE nome=?", (conta_nome,)).fetchone()
        lid = criar_lancamento(
            conn, tipo="Despesa", valor=total_geral,
            descricao="Compra gado - " + str(len(animais)) + " animais - " + (vendedor or "sem vendedor"),
            categoria="Gado",
            id_conta=id_conta["id"] if id_conta else None,
            data=data_compra, status=status_fin, origem="compra_lote",
        )
        for a in animais:
            cur = conn.execute("""INSERT INTO animal
                (brinco, sexo, categoria, raca, origem, data_entrada, status)
                VALUES (?,?,?,?,'Comprado',?,'Ativo')""",
                (a["brinco"], a["sexo"], a["categoria"], a["raca"], data_compra))
            id_animal = cur.lastrowid
            conn.execute("""INSERT INTO movimentacao
                (id_animal, tipo, data, peso_kg, valor_arroba, valor_total,
                 contraparte, nota_fiscal, id_conta, id_lancamento, status_fin)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (id_animal, "Compra", data_compra,
                 a["peso_kg"], valor_arroba, a["valor_total"],
                 vendedor, nota_fiscal,
                 id_conta["id"] if id_conta else None, lid, status_fin))
        conn.commit()
        flash(stdscr, "Compra gravada! " + str(len(animais)) + " animais. Lancamento #" + str(lid) + ": R$ " + f"{total_geral:,.2f}")
    except sqlite3.IntegrityError as e:
        conn.rollback()
        flash(stdscr, "Erro - brinco duplicado: " + str(e), error=True)
    except Exception as e:
        conn.rollback()
        flash(stdscr, "Erro: " + str(e), error=True)
    finally:
        conn.close()


# ═════════════════════════════════════════════════════
# NASCIMENTO
# ═════════════════════════════════════════════════════
def _garantir_lote_bezerros(conn):
    ano = date.today().year
    nome_lote = "Bezerros " + str(ano)
    row = conn.execute("SELECT id FROM lote WHERE nome=?", (nome_lote,)).fetchone()
    if row:
        return row["id"]
    pasto = conn.execute("SELECT id FROM pasto LIMIT 1").fetchone()
    cur = conn.execute(
        "INSERT INTO lote (nome, fase, id_pasto, data_inicio) VALUES (?,?,?,?)",
        (nome_lote, "Cria", pasto["id"] if pasto else None, date.today().isoformat()))
    return cur.lastrowid


def _alocar_animal_lote(conn, id_animal, id_lote):
    hoje = date.today().isoformat()
    conn.execute("UPDATE animal_lote SET data_saida=? WHERE id_animal=? AND data_saida IS NULL",
                 (hoje, id_animal))
    conn.execute("INSERT INTO animal_lote (id_animal, id_lote, data_entrada) VALUES (?,?,?)",
                 (id_animal, id_lote, hoje))


def registrar_nascimento(stdscr):
    h, w = stdscr.getmaxyx()
    win = curses.newwin(5, 36, h//2-3, max(0, w//2-18))
    win.erase()
    draw_box(win, " Nascimento - Brinco da Mae ")
    safe_addstr(win, 2, 2, "Brinco da mae: ", TITLE())
    win.refresh()
    brinco_mae = text_input(win, 2, 17, 12, "")
    if not brinco_mae.strip():
        return

    conn = get_db()
    mae = conn.execute(
        "SELECT id, brinco, raca, categoria FROM animal WHERE brinco=? AND sexo='F'",
        (brinco_mae.strip(),)).fetchone()
    if not mae:
        conn.close()
        flash(stdscr, "Femea " + brinco_mae + " nao encontrada.", error=True)
        return

    cobertura = conn.execute(
        "SELECT id, id_touro FROM reproducao WHERE id_femea=? AND data_parto_real IS NULL AND resultado_dg='Positivo' ORDER BY data_cobertura DESC LIMIT 1",
        (mae["id"],)).fetchone()

    touro_brinco = ""
    if cobertura and cobertura["id_touro"]:
        t = conn.execute("SELECT brinco FROM animal WHERE id=?", (cobertura["id_touro"],)).fetchone()
        touro_brinco = t["brinco"] if t else ""
    conn.close()

    fields = [
        {"label": "Brinco Bezerro",  "required": True},
        {"label": "Sexo",            "required": True, "options": ["M","F"]},
        {"label": "Data Nasc.",      "default": date.today().isoformat()},
        {"label": "Peso Nasc. (kg)", "default": ""},
        {"label": "Raca",            "default": mae["raca"] or ""},
        {"label": "Brinco Pai",      "default": touro_brinco},
        {"label": "Obs."},
    ]
    result = form(stdscr, fields, title=" Nascimento - Mae: " + mae["brinco"] + " ", width=54)
    if result is None:
        return

    conn = get_db()
    try:
        sexo      = result["Sexo"]
        categoria = "Bezerro" if sexo == "M" else "Bezerra"
        data_nasc = result["Data Nasc."] or date.today().isoformat()
        peso_s    = result["Peso Nasc. (kg)"].replace(",",".") if result["Peso Nasc. (kg)"] else ""
        peso_nasc = float(peso_s) if peso_s else None

        id_pai = None
        if result["Brinco Pai"].strip():
            pai = conn.execute("SELECT id FROM animal WHERE brinco=?",
                               (result["Brinco Pai"].strip(),)).fetchone()
            id_pai = pai["id"] if pai else None

        cur = conn.execute("""INSERT INTO animal
            (brinco, sexo, categoria, raca, origem,
             data_nascimento, peso_nascimento,
             id_mae, id_pai, data_entrada, status)
            VALUES (?,?,?,?,'Nascido',?,?,?,?,?,'Ativo')""",
            (result["Brinco Bezerro"].strip(), sexo, categoria,
             result["Raca"] or None, data_nasc, peso_nasc,
             mae["id"], id_pai, data_nasc))
        id_bezerro = cur.lastrowid

        id_lote = _garantir_lote_bezerros(conn)
        _alocar_animal_lote(conn, id_bezerro, id_lote)

        if cobertura:
            conn.execute("UPDATE reproducao SET data_parto_real=?, id_cria=? WHERE id=?",
                         (data_nasc, id_bezerro, cobertura["id"]))

        conn.commit()
        lote_nome = conn.execute("SELECT nome FROM lote WHERE id=?", (id_lote,)).fetchone()["nome"]
        msg = "Nascimento gravado! " + categoria + " " + result["Brinco Bezerro"] + " -> lote '" + lote_nome + "'"
        if cobertura:
            msg += " - cobertura fechada."
        flash(stdscr, msg)
    except sqlite3.IntegrityError:
        conn.rollback()
        flash(stdscr, "Brinco " + result["Brinco Bezerro"] + " ja existe.", error=True)
    except ValueError:
        conn.rollback()
        flash(stdscr, "Peso invalido.", error=True)
    finally:
        conn.close()


def _recalcular_arroba_compra(conn, id_animal):
    """Calcula valor/@ retroativamente quando primeiro peso eh registrado."""
    mov = conn.execute(
        "SELECT id, valor_total FROM movimentacao WHERE id_animal=? AND tipo='Compra' AND valor_arroba IS NULL AND valor_total IS NOT NULL",
        (id_animal,)).fetchone()
    if not mov:
        return
    peso = conn.execute(
        "SELECT peso_kg FROM pesagem WHERE id_animal=? ORDER BY data_pesagem ASC LIMIT 1",
        (id_animal,)).fetchone()
    if not peso or not peso["peso_kg"]:
        return
    arroba = mov["valor_total"] / peso["peso_kg"] * 15
    conn.execute("UPDATE movimentacao SET peso_kg=?, valor_arroba=? WHERE id=?",
                 (peso["peso_kg"], round(arroba, 2), mov["id"]))

def main():
    migrate_db_path()
    init_db()
    try:
        curses.wrapper(main_loop)
    except KeyboardInterrupt:
        pass
    print("\n🏡  Até logo!\n")

if __name__ == "__main__":
    main()
