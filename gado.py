#!/usr/bin/env python3
"""
gado - Sistema de Gerenciamento de Gado
Fazenda de cria, recria e engorda
"""

import sqlite3
import argparse
import sys
import os
from datetime import date, datetime

DB_PATH = os.path.expanduser("~/.gado.db")

# ─────────────────────────────────────────────
# CORES (ANSI)
# ─────────────────────────────────────────────
R = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
DIM = "\033[2m"

def cor(texto, *codes):
    return "".join(codes) + str(texto) + R

def titulo(texto):
    print()
    print(cor(f"  {texto}", BOLD, CYAN))
    print(cor("  " + "─" * len(texto), DIM))

def ok(msg):   print(cor(f"  ✔  {msg}", GREEN))
def err(msg):  print(cor(f"  ✖  {msg}", RED)); sys.exit(1)
def aviso(msg): print(cor(f"  ⚠  {msg}", YELLOW))

def tabela(colunas, linhas, larguras=None):
    if not larguras:
        larguras = [max(len(str(c)), max((len(str(l[i])) for l in linhas), default=0))
                    for i, c in enumerate(colunas)]
    sep = "  "
    header = sep.join(cor(str(c).ljust(w), BOLD) for c, w in zip(colunas, larguras))
    print("  " + header)
    print("  " + cor("─" * (sum(larguras) + len(sep) * (len(colunas) - 1)), DIM))
    for i, linha in enumerate(linhas):
        row = sep.join(str(v if v is not None else "—").ljust(w) for v, w in zip(linha, larguras))
        bg = DIM if i % 2 == 0 else ""
        print("  " + cor(row, bg))
    print()

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
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS pasto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        area_ha REAL,
        forrageira TEXT,
        capacidade_ua INTEGER,
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS animal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brinco TEXT NOT NULL UNIQUE,
        sisbov TEXT,
        nome TEXT,
        sexo TEXT CHECK(sexo IN ('M','F')) NOT NULL,
        categoria TEXT CHECK(categoria IN ('Bezerro','Bezerra','Novilho','Novilha','Vaca','Touro','Boi')) NOT NULL,
        raca TEXT,
        data_nascimento TEXT,
        peso_nascimento REAL,
        id_mae INTEGER REFERENCES animal(id),
        id_pai INTEGER REFERENCES animal(id),
        origem TEXT CHECK(origem IN ('Nascido','Comprado')) DEFAULT 'Nascido',
        fazenda_origem TEXT,
        status TEXT CHECK(status IN ('Ativo','Vendido','Morto','Descartado')) DEFAULT 'Ativo',
        data_entrada TEXT DEFAULT (date('now')),
        data_saida TEXT,
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS lote (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        fase TEXT CHECK(fase IN ('Cria','Recria','Engorda')) NOT NULL,
        id_pasto INTEGER REFERENCES pasto(id),
        data_inicio TEXT DEFAULT (date('now')),
        data_fim TEXT,
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS animal_lote (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        id_lote INTEGER NOT NULL REFERENCES lote(id),
        data_entrada TEXT DEFAULT (date('now')),
        data_saida TEXT
    );

    CREATE TABLE IF NOT EXISTS pesagem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        data_pesagem TEXT NOT NULL DEFAULT (date('now')),
        peso_kg REAL NOT NULL,
        fase TEXT CHECK(fase IN ('Cria','Recria','Engorda')),
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS reproducao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_femea INTEGER NOT NULL REFERENCES animal(id),
        id_touro INTEGER REFERENCES animal(id),
        tipo TEXT CHECK(tipo IN ('Monta Natural','IA','IATF')) DEFAULT 'Monta Natural',
        data_cobertura TEXT,
        data_dg TEXT,
        resultado_dg TEXT CHECK(resultado_dg IN ('Positivo','Negativo','Vazia')),
        data_parto_previsto TEXT,
        data_parto_real TEXT,
        id_cria INTEGER REFERENCES animal(id),
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS sanidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER REFERENCES animal(id),
        id_lote INTEGER REFERENCES lote(id),
        data TEXT NOT NULL DEFAULT (date('now')),
        tipo TEXT CHECK(tipo IN ('Vacina','Vermífugo','Carrapaticida','Exame','Outro')) NOT NULL,
        produto TEXT,
        dose_ml REAL,
        lote_produto TEXT,
        responsavel TEXT,
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS movimentacao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        tipo TEXT CHECK(tipo IN ('Compra','Venda')) NOT NULL,
        data TEXT NOT NULL DEFAULT (date('now')),
        peso_kg REAL,
        valor_arroba REAL,
        valor_total REAL,
        contraparte TEXT,
        nota_fiscal TEXT,
        observacao TEXT
    );

    CREATE TABLE IF NOT EXISTS mortalidade (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_animal INTEGER NOT NULL REFERENCES animal(id),
        data TEXT NOT NULL DEFAULT (date('now')),
        causa TEXT,
        laudo TEXT
    );
    """)
    conn.commit()

    # Migration: adiciona colunas novas em bancos já existentes
    colunas = [r[1] for r in conn.execute("PRAGMA table_info(animal)").fetchall()]
    if "fazenda_origem" not in colunas:
        conn.execute("ALTER TABLE animal ADD COLUMN fazenda_origem TEXT")
        conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def animal_id_por_brinco(conn, brinco):
    row = conn.execute("SELECT id FROM animal WHERE brinco=?", (brinco,)).fetchone()
    if not row:
        err(f"Animal com brinco '{brinco}' não encontrado.")
    return row["id"]

def lote_id_por_nome(conn, nome):
    row = conn.execute("SELECT id FROM lote WHERE nome=?", (nome,)).fetchone()
    if not row:
        err(f"Lote '{nome}' não encontrado.")
    return row["id"]

def pasto_id_por_nome(conn, nome):
    row = conn.execute("SELECT id FROM pasto WHERE nome=?", (nome,)).fetchone()
    if not row:
        err(f"Pasto '{nome}' não encontrado.")
    return row["id"]

# ─────────────────────────────────────────────────────
# COMANDOS: ANIMAL
# ─────────────────────────────────────────────────────
def cmd_animal_add(a):
    conn = get_db()
    id_mae = animal_id_por_brinco(conn, a.mae) if a.mae else None
    id_pai = animal_id_por_brinco(conn, a.pai) if a.pai else None
    try:
        conn.execute("""INSERT INTO animal
            (brinco,sisbov,nome,sexo,categoria,raca,data_nascimento,peso_nascimento,
             id_mae,id_pai,origem,fazenda_origem,observacao)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (a.brinco, a.sisbov, a.nome, a.sexo.upper(), a.categoria, a.raca,
             a.nascimento, a.peso, id_mae, id_pai, a.origem, a.fazenda_origem, a.obs))
        conn.commit()
        ok(f"Animal {a.brinco} cadastrado com sucesso.")

        # Registra compra automaticamente se origem=Comprado e valores fornecidos
        if a.origem == "Comprado":
            aid = conn.execute("SELECT id FROM animal WHERE brinco=?", (a.brinco,)).fetchone()["id"]
            valor_total = None
            if a.peso_entrada and a.valor_arroba:
                valor_total = (a.peso_entrada / 15) * a.valor_arroba
            conn.execute("""INSERT INTO movimentacao
                (id_animal,tipo,data,peso_kg,valor_arroba,valor_total,contraparte,nota_fiscal,observacao)
                VALUES (?,?,date('now'),?,?,?,?,?,?)""",
                (aid, 'Compra', a.peso_entrada, a.valor_arroba, valor_total,
                 getattr(a,'vendedor',None), getattr(a,'nf',None), a.obs))
            conn.commit()
            if valor_total:
                ok(f"Compra registrada: R$ {valor_total:.2f} ({a.peso_entrada} kg @ R$ {a.valor_arroba}/arroba)")
    except sqlite3.IntegrityError as e:
        err(str(e))
    conn.close()

def cmd_animal_list(a):
    conn = get_db()
    where = "WHERE 1=1"
    params = []
    if a.status:
        where += " AND status=?"; params.append(a.status)
    if a.categoria:
        where += " AND categoria=?"; params.append(a.categoria)
    if a.sexo:
        where += " AND sexo=?"; params.append(a.sexo.upper())
    rows = conn.execute(f"""
        SELECT brinco, nome, sexo, categoria, raca, data_nascimento, status, origem
        FROM animal {where} ORDER BY brinco
    """, params).fetchall()
    titulo(f"Animais ({len(rows)} encontrados)")
    if rows:
        tabela(
            ["Brinco","Nome","Sx","Categoria","Raça","Nascimento","Status","Origem"],
            [[r["brinco"],r["nome"],r["sexo"],r["categoria"],r["raca"],
              r["data_nascimento"],r["status"],r["origem"]] for r in rows],
            [10,12,3,10,10,12,10,8]
        )
    conn.close()

def cmd_animal_show(a):
    conn = get_db()
    row = conn.execute("""
        SELECT a.*, m.brinco as brinco_mae, p.brinco as brinco_pai
        FROM animal a
        LEFT JOIN animal m ON a.id_mae=m.id
        LEFT JOIN animal p ON a.id_pai=p.id
        WHERE a.brinco=?
    """, (a.brinco,)).fetchone()
    if not row:
        err(f"Animal '{a.brinco}' não encontrado.")
    titulo(f"Animal: {row['brinco']}")
    campos = [
        ("Brinco", row["brinco"]), ("SISBOV", row["sisbov"]),
        ("Nome", row["nome"]), ("Sexo", row["sexo"]),
        ("Categoria", row["categoria"]), ("Raça", row["raca"]),
        ("Nascimento", row["data_nascimento"]), ("Peso Nasc.", row["peso_nascimento"]),
        ("Mãe", row["brinco_mae"]), ("Pai", row["brinco_pai"]),
        ("Origem", row["origem"]), ("Fazenda Origem", row["fazenda_origem"]), ("Status", row["status"]),
        ("Entrada", row["data_entrada"]), ("Saída", row["data_saida"]),
        ("Obs.", row["observacao"]),
    ]
    for k, v in campos:
        if v:
            print(f"  {cor(k+':',BOLD)} {v}")

    # Últimas pesagens
    pesos = conn.execute("""SELECT data_pesagem, peso_kg, fase FROM pesagem
        WHERE id_animal=? ORDER BY data_pesagem DESC LIMIT 5""", (row["id"],)).fetchall()
    if pesos:
        titulo("Últimas pesagens")
        tabela(["Data","Peso (kg)","Fase"], [[p["data_pesagem"],p["peso_kg"],p["fase"]] for p in pesos])
    print()
    conn.close()

def cmd_animal_update(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    campos = []
    vals = []
    if a.status:   campos.append("status=?");   vals.append(a.status)
    if a.categoria: campos.append("categoria=?"); vals.append(a.categoria)
    if a.nome:     campos.append("nome=?");      vals.append(a.nome)
    if a.raca:     campos.append("raca=?");      vals.append(a.raca)
    if a.sisbov:   campos.append("sisbov=?");    vals.append(a.sisbov)
    if a.obs:      campos.append("observacao=?");      vals.append(a.obs)
    if a.origem:        campos.append("origem=?");         vals.append(a.origem)
    if a.fazenda_origem: campos.append("fazenda_origem=?"); vals.append(a.fazenda_origem)
    if not campos:
        aviso("Nenhum campo para atualizar."); return
    vals.append(aid)
    conn.execute(f"UPDATE animal SET {', '.join(campos)} WHERE id=?", vals)
    conn.commit()
    ok(f"Animal {a.brinco} atualizado.")
    conn.close()


def cmd_animal_delete(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    deps = {
        "pesagens":      conn.execute("SELECT COUNT(*) FROM pesagem WHERE id_animal=?", (aid,)).fetchone()[0],
        "movimentacoes": conn.execute("SELECT COUNT(*) FROM movimentacao WHERE id_animal=?", (aid,)).fetchone()[0],
        "sanidades":     conn.execute("SELECT COUNT(*) FROM sanidade WHERE id_animal=?", (aid,)).fetchone()[0],
        "reproducoes":   conn.execute("SELECT COUNT(*) FROM reproducao WHERE id_femea=? OR id_touro=? OR id_cria=?", (aid,aid,aid)).fetchone()[0],
        "mortalidade":   conn.execute("SELECT COUNT(*) FROM mortalidade WHERE id_animal=?", (aid,)).fetchone()[0],
    }
    tem_deps = any(v > 0 for v in deps.values())
    if tem_deps and not a.force:
        aviso(f"Animal {a.brinco} possui registros vinculados:")
        for k, v in deps.items():
            if v > 0:
                print(f"     {v} {k}")
        print(cor(f"\n  Use --force para deletar mesmo assim (apaga todos os registros vinculados).", YELLOW))
        conn.close()
        return
    conn.execute("DELETE FROM pesagem WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM movimentacao WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM sanidade WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM reproducao WHERE id_femea=? OR id_touro=? OR id_cria=?", (aid,aid,aid))
    conn.execute("DELETE FROM mortalidade WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM animal_lote WHERE id_animal=?", (aid,))
    conn.execute("DELETE FROM animal WHERE id=?", (aid,))
    conn.commit()
    ok(f"Animal {a.brinco} deletado com sucesso.")
    conn.close()
def cmd_animal_baixa(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    hoje = date.today().isoformat()
    if a.tipo == "morte":
        conn.execute("UPDATE animal SET status='Morto', data_saida=? WHERE id=?", (hoje, aid))
        conn.execute("INSERT INTO mortalidade (id_animal, data, causa, laudo) VALUES (?,?,?,?)",
                     (aid, hoje, a.causa, a.laudo))
        ok(f"Animal {a.brinco} registrado como morto.")
    elif a.tipo == "venda":
        conn.execute("UPDATE animal SET status='Vendido', data_saida=? WHERE id=?", (hoje, aid))
        valor_total = None
        if a.peso and a.valor_arroba:
            valor_total = (a.peso / 15) * a.valor_arroba
        conn.execute("""INSERT INTO movimentacao
            (id_animal,tipo,data,peso_kg,valor_arroba,valor_total,contraparte,nota_fiscal,observacao)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (aid,'Venda',hoje,a.peso,a.valor_arroba,valor_total,a.comprador,a.nf,a.obs))
        msg = f"Animal {a.brinco} vendido"
        if valor_total:
            msg += f" | Valor total: R$ {valor_total:.2f}"
        ok(msg)
    elif a.tipo == "descarte":
        conn.execute("UPDATE animal SET status='Descartado', data_saida=? WHERE id=?", (hoje, aid))
        ok(f"Animal {a.brinco} descartado.")
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────────────
# COMANDOS: PASTO
# ─────────────────────────────────────────────────────
def cmd_pasto_add(a):
    conn = get_db()
    try:
        conn.execute("INSERT INTO pasto (nome,area_ha,forrageira,capacidade_ua,observacao) VALUES (?,?,?,?,?)",
                     (a.nome, a.area, a.forrageira, a.capacidade, a.obs))
        conn.commit()
        ok(f"Pasto '{a.nome}' cadastrado.")
    except sqlite3.IntegrityError:
        err(f"Pasto '{a.nome}' já existe.")
    conn.close()

def cmd_pasto_list(a):
    conn = get_db()
    rows = conn.execute("SELECT nome, area_ha, forrageira, capacidade_ua FROM pasto ORDER BY nome").fetchall()
    titulo("Pastos")
    if rows:
        tabela(["Nome","Área (ha)","Forrageira","Cap. UA"],
               [[r["nome"],r["area_ha"],r["forrageira"],r["capacidade_ua"]] for r in rows])
    conn.close()

# ─────────────────────────────────────────────────────
# COMANDOS: LOTE
# ─────────────────────────────────────────────────────
def cmd_lote_add(a):
    conn = get_db()
    id_pasto = pasto_id_por_nome(conn, a.pasto) if a.pasto else None
    try:
        conn.execute("INSERT INTO lote (nome,fase,id_pasto,observacao) VALUES (?,?,?,?)",
                     (a.nome, a.fase, id_pasto, a.obs))
        conn.commit()
        ok(f"Lote '{a.nome}' cadastrado (fase: {a.fase}).")
    except sqlite3.IntegrityError:
        err(f"Lote '{a.nome}' já existe.")
    conn.close()

def cmd_lote_list(a):
    conn = get_db()
    rows = conn.execute("""
        SELECT l.nome, l.fase, p.nome as pasto, l.data_inicio, l.data_fim,
               COUNT(al.id) as qtd
        FROM lote l
        LEFT JOIN pasto p ON l.id_pasto=p.id
        LEFT JOIN animal_lote al ON l.id=al.id_lote AND al.data_saida IS NULL
        GROUP BY l.id ORDER BY l.nome
    """).fetchall()
    titulo("Lotes")
    if rows:
        tabela(["Nome","Fase","Pasto","Início","Fim","Animais"],
               [[r["nome"],r["fase"],r["pasto"],r["data_inicio"],r["data_fim"],r["qtd"]] for r in rows])
    conn.close()

def cmd_lote_adicionar_animal(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    lid = lote_id_por_nome(conn, a.lote)
    # Fecha lote anterior se houver
    conn.execute("""UPDATE animal_lote SET data_saida=date('now')
        WHERE id_animal=? AND data_saida IS NULL""", (aid,))
    conn.execute("INSERT INTO animal_lote (id_animal,id_lote) VALUES (?,?)", (aid, lid))
    conn.commit()
    ok(f"Animal {a.brinco} adicionado ao lote '{a.lote}'.")
    conn.close()

def cmd_lote_show(a):
    conn = get_db()
    lid = lote_id_por_nome(conn, a.nome)
    rows = conn.execute("""
        SELECT an.brinco, an.nome, an.sexo, an.categoria, an.raca, al.data_entrada
        FROM animal_lote al
        JOIN animal an ON al.id_animal=an.id
        WHERE al.id_lote=? AND al.data_saida IS NULL
        ORDER BY an.brinco
    """, (lid,)).fetchall()
    titulo(f"Animais no lote '{a.nome}' ({len(rows)})")
    if rows:
        tabela(["Brinco","Nome","Sx","Categoria","Raça","Entrada"],
               [[r["brinco"],r["nome"],r["sexo"],r["categoria"],r["raca"],r["data_entrada"]] for r in rows])
    conn.close()

# ─────────────────────────────────────────────────────
# COMANDOS: PESAGEM
# ─────────────────────────────────────────────────────
def cmd_pesagem_add(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    hoje = date.today().isoformat()
    data = a.data or hoje
    conn.execute("INSERT INTO pesagem (id_animal,data_pesagem,peso_kg,fase,observacao) VALUES (?,?,?,?,?)",
                 (aid, data, a.peso, a.fase, a.obs))
    conn.commit()

    # Calcula GMD
    anterior = conn.execute("""SELECT peso_kg, data_pesagem FROM pesagem
        WHERE id_animal=? AND data_pesagem < ? ORDER BY data_pesagem DESC LIMIT 1""",
        (aid, data)).fetchone()
    msg = f"Pesagem registrada: {a.peso} kg em {data}"
    if anterior:
        dias = (datetime.fromisoformat(data) - datetime.fromisoformat(anterior["data_pesagem"])).days
        if dias > 0:
            gmd = (a.peso - anterior["peso_kg"]) / dias
            msg += f" | GMD: {gmd:.3f} kg/dia ({dias} dias)"
    ok(msg)
    conn.close()

def cmd_pesagem_lote(a):
    """Registra pesagem para todos os animais de um lote"""
    conn = get_db()
    lid = lote_id_por_nome(conn, a.lote)
    hoje = date.today().isoformat()
    data = a.data or hoje
    rows = conn.execute("""SELECT an.id, an.brinco FROM animal_lote al
        JOIN animal an ON al.id_animal=an.id
        WHERE al.id_lote=? AND al.data_saida IS NULL""", (lid,)).fetchall()
    if not rows:
        aviso("Nenhum animal no lote."); return

    print()
    print(cor(f"  Pesagem do lote '{a.lote}' — {data}", BOLD))
    print(cor("  (Digite o peso em kg ou ENTER para pular)\n", DIM))
    registrados = 0
    for row in rows:
        try:
            entrada = input(f"  {cor(row['brinco'], CYAN)}: ")
            if entrada.strip():
                peso = float(entrada.strip())
                conn.execute("INSERT INTO pesagem (id_animal,data_pesagem,peso_kg,fase) VALUES (?,?,?,?)",
                             (row["id"], data, peso, a.fase))
                registrados += 1
        except (ValueError, KeyboardInterrupt):
            pass
    conn.commit()
    ok(f"{registrados} pesagens registradas para o lote '{a.lote}'.")
    conn.close()

def cmd_pesagem_historico(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    rows = conn.execute("""SELECT data_pesagem, peso_kg, fase, observacao
        FROM pesagem WHERE id_animal=? ORDER BY data_pesagem""", (aid,)).fetchall()
    titulo(f"Histórico de pesagens: {a.brinco}")
    if len(rows) < 2:
        tabela(["Data","Peso (kg)","Fase","Obs"], [[r["data_pesagem"],r["peso_kg"],r["fase"],r["observacao"]] for r in rows])
    else:
        dados = []
        for i, r in enumerate(rows):
            if i == 0:
                dados.append([r["data_pesagem"], r["peso_kg"], r["fase"], "—", r["observacao"]])
            else:
                ant = rows[i-1]
                dias = (datetime.fromisoformat(r["data_pesagem"]) - datetime.fromisoformat(ant["data_pesagem"])).days
                gmd = f"{(r['peso_kg']-ant['peso_kg'])/dias:.3f}" if dias > 0 else "—"
                dados.append([r["data_pesagem"], r["peso_kg"], r["fase"], gmd, r["observacao"]])
        tabela(["Data","Peso (kg)","Fase","GMD (kg/d)","Obs"], dados)
    conn.close()

# ─────────────────────────────────────────────────────
# COMANDOS: REPRODUÇÃO
# ─────────────────────────────────────────────────────
def cmd_repro_add(a):
    conn = get_db()
    fid = animal_id_por_brinco(conn, a.femea)
    tid = animal_id_por_brinco(conn, a.touro) if a.touro else None
    conn.execute("""INSERT INTO reproducao
        (id_femea,id_touro,tipo,data_cobertura,observacao)
        VALUES (?,?,?,?,?)""",
        (fid, tid, a.tipo, a.data, a.obs))
    conn.commit()
    ok(f"Cobertura registrada para fêmea {a.femea} ({a.tipo}) em {a.data}.")
    conn.close()

def cmd_repro_dg(a):
    conn = get_db()
    fid = animal_id_por_brinco(conn, a.femea)
    conn.execute("""UPDATE reproducao SET data_dg=?, resultado_dg=?, data_parto_previsto=?
        WHERE id_femea=? AND data_dg IS NULL ORDER BY id DESC LIMIT 1""",
        (a.data, a.resultado, a.parto_previsto, fid))
    conn.commit()
    ok(f"DG registrado para {a.femea}: {a.resultado} | Parto previsto: {a.parto_previsto}")
    conn.close()

def cmd_repro_parto(a):
    conn = get_db()
    fid = animal_id_por_brinco(conn, a.femea)
    cid = animal_id_por_brinco(conn, a.cria) if a.cria else None
    conn.execute("""UPDATE reproducao SET data_parto_real=?, id_cria=?
        WHERE id_femea=? AND data_parto_real IS NULL ORDER BY id DESC LIMIT 1""",
        (a.data, cid, fid))
    conn.commit()
    ok(f"Parto registrado para {a.femea} em {a.data}." + (f" Cria: {a.cria}" if a.cria else ""))
    conn.close()

def cmd_repro_list(a):
    conn = get_db()
    rows = conn.execute("""
        SELECT f.brinco as femea, t.brinco as touro, r.tipo,
               r.data_cobertura, r.resultado_dg, r.data_parto_previsto, r.data_parto_real,
               c.brinco as cria
        FROM reproducao r
        JOIN animal f ON r.id_femea=f.id
        LEFT JOIN animal t ON r.id_touro=t.id
        LEFT JOIN animal c ON r.id_cria=c.id
        ORDER BY r.data_cobertura DESC LIMIT 50
    """).fetchall()
    titulo("Reprodução (últimos 50 registros)")
    if rows:
        tabela(["Fêmea","Touro","Tipo","Cobertura","DG","Parto Prev.","Parto Real","Cria"],
               [[r["femea"],r["touro"],r["tipo"],r["data_cobertura"],r["resultado_dg"],
                 r["data_parto_previsto"],r["data_parto_real"],r["cria"]] for r in rows],
               [8,8,14,10,10,12,12,8])
    conn.close()

# ─────────────────────────────────────────────────────
# COMANDOS: SANIDADE
# ─────────────────────────────────────────────────────
def cmd_sanidade_add(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco) if a.brinco else None
    lid = lote_id_por_nome(conn, a.lote) if a.lote else None
    if not aid and not lid:
        err("Informe --brinco ou --lote.")
    conn.execute("""INSERT INTO sanidade
        (id_animal,id_lote,data,tipo,produto,dose_ml,lote_produto,responsavel,observacao)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (aid, lid, a.data or date.today().isoformat(), a.tipo, a.produto,
         a.dose, a.lote_produto, a.responsavel, a.obs))
    conn.commit()
    alvo = f"animal {a.brinco}" if a.brinco else f"lote '{a.lote}'"
    ok(f"{a.tipo} de {a.produto} registrada para {alvo}.")
    conn.close()

def cmd_sanidade_list(a):
    conn = get_db()
    rows = conn.execute("""
        SELECT s.data, an.brinco as animal, l.nome as lote, s.tipo, s.produto, s.dose_ml, s.responsavel
        FROM sanidade s
        LEFT JOIN animal an ON s.id_animal=an.id
        LEFT JOIN lote l ON s.id_lote=l.id
        ORDER BY s.data DESC LIMIT 50
    """).fetchall()
    titulo("Sanidade (últimos 50)")
    if rows:
        tabela(["Data","Animal","Lote","Tipo","Produto","Dose(ml)","Responsável"],
               [[r["data"],r["animal"],r["lote"],r["tipo"],r["produto"],r["dose_ml"],r["responsavel"]] for r in rows],
               [10,8,12,12,16,9,14])
    conn.close()


# ─────────────────────────────────────────────────────
# COMANDOS: MOVIMENTAÇÃO
# ─────────────────────────────────────────────────────
def cmd_mov_add(a):
    conn = get_db()
    aid = animal_id_por_brinco(conn, a.brinco)
    valor_total = None
    if a.peso and a.valor_arroba:
        valor_total = (a.peso / 15) * a.valor_arroba
    conn.execute("""INSERT INTO movimentacao
        (id_animal,tipo,data,peso_kg,valor_arroba,valor_total,contraparte,nota_fiscal,observacao)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (aid, a.tipo, a.data or date.today().isoformat(),
         a.peso, a.valor_arroba, valor_total,
         a.contraparte, a.nf, a.obs))
    conn.commit()
    msg = f"Movimentação de {a.tipo} registrada para {a.brinco}"
    if valor_total:
        msg += f" | Valor total: R$ {valor_total:.2f}"
    ok(msg)
    conn.close()

def cmd_mov_list(a):
    conn = get_db()
    where = "WHERE 1=1"
    params = []
    if a.brinco:
        aid = animal_id_por_brinco(conn, a.brinco)
        where += " AND m.id_animal=?"; params.append(aid)
    if a.tipo:
        where += " AND m.tipo=?"; params.append(a.tipo)
    rows = conn.execute(f"""
        SELECT m.id, an.brinco, m.tipo, m.data, m.peso_kg,
               m.valor_arroba, m.valor_total, m.contraparte, m.nota_fiscal
        FROM movimentacao m JOIN animal an ON m.id_animal=an.id
        {where} ORDER BY m.data DESC, m.id DESC
    """, params).fetchall()
    titulo("Movimentações")
    if rows:
        tabela(["ID","Brinco","Tipo","Data","Peso(kg)","R$/@","Total","Contraparte"],
               [[r["id"],r["brinco"],r["tipo"],r["data"],r["peso_kg"],
                 r["valor_arroba"],("R$ %.2f"%r["valor_total"]) if r["valor_total"] else None,
                 r["contraparte"]] for r in rows],
               [5,10,8,10,9,8,12,16])
    conn.close()

def cmd_mov_update(a):
    conn = get_db()
    row = conn.execute("SELECT * FROM movimentacao WHERE id=?", (a.id,)).fetchone()
    if not row:
        err(f"Movimentação ID {a.id} não encontrada. Use 'gado mov list' para ver os IDs.")
    campos = []
    vals = []
    if a.peso is not None:         campos.append("peso_kg=?");       vals.append(a.peso)
    if a.valor_arroba is not None: campos.append("valor_arroba=?");  vals.append(a.valor_arroba)
    if a.data:                     campos.append("data=?");           vals.append(a.data)
    if a.contraparte:              campos.append("contraparte=?");    vals.append(a.contraparte)
    if a.nf:                       campos.append("nota_fiscal=?");    vals.append(a.nf)
    if a.obs:                      campos.append("observacao=?");     vals.append(a.obs)
    if not campos:
        aviso("Nenhum campo para atualizar."); return
    # Recalcula valor_total se peso ou arroba foram alterados
    peso = a.peso if a.peso is not None else row["peso_kg"]
    arroba = a.valor_arroba if a.valor_arroba is not None else row["valor_arroba"]
    if peso and arroba:
        campos.append("valor_total=?")
        vals.append((peso / 15) * arroba)
    vals.append(a.id)
    conn.execute(f"UPDATE movimentacao SET {', '.join(campos)} WHERE id=?", vals)
    conn.commit()
    # Mostra resultado
    updated = conn.execute("SELECT * FROM movimentacao WHERE id=?", (a.id,)).fetchone()
    ok(f"Movimentação {a.id} atualizada.")
    if updated["valor_total"]:
        print(f"  {cor('Valor total recalculado:', BOLD)} R$ {updated['valor_total']:.2f}")
    conn.close()

def cmd_mov_delete(a):
    conn = get_db()
    row = conn.execute("SELECT * FROM movimentacao WHERE id=?", (a.id,)).fetchone()
    if not row:
        err(f"Movimentação ID {a.id} não encontrada.")
    conn.execute("DELETE FROM movimentacao WHERE id=?", (a.id,))
    conn.commit()
    ok(f"Movimentação {a.id} deletada.")
    conn.close()
# ─────────────────────────────────────────────────────
# COMANDOS: RELATÓRIOS
# ─────────────────────────────────────────────────────
def cmd_relatorio_rebanho(a):
    conn = get_db()
    titulo("Resumo do Rebanho")
    rows = conn.execute("""
        SELECT categoria, sexo, COUNT(*) as qtd
        FROM animal WHERE status='Ativo'
        GROUP BY categoria, sexo ORDER BY categoria, sexo
    """).fetchall()
    tabela(["Categoria","Sexo","Qtd"], [[r["categoria"],r["sexo"],r["qtd"]] for r in rows])

    total = conn.execute("SELECT COUNT(*) as n FROM animal WHERE status='Ativo'").fetchone()["n"]
    print(f"  {cor('Total ativo:', BOLD)} {cor(total, GREEN, BOLD)}")
    print()

    # Por status
    st = conn.execute("SELECT status, COUNT(*) as n FROM animal GROUP BY status").fetchall()
    titulo("Por status")
    tabela(["Status","Qtd"], [[r["status"],r["n"]] for r in st])
    conn.close()

def cmd_relatorio_gmd(a):
    conn = get_db()
    where = ""
    params = []
    if a.fase:
        where = "AND p.fase=?"; params.append(a.fase)
    rows = conn.execute(f"""
        SELECT an.brinco, an.categoria,
               MIN(p.data_pesagem) as inicio,
               MAX(p.data_pesagem) as fim,
               MIN(p.peso_kg) as peso_ini,
               MAX(p.peso_kg) as peso_fim,
               COUNT(p.id) as n_pesagens
        FROM pesagem p
        JOIN animal an ON p.id_animal=an.id
        WHERE an.status='Ativo' {where}
        GROUP BY p.id_animal HAVING n_pesagens >= 2
        ORDER BY an.brinco
    """, params).fetchall()
    fase_str = f" ({a.fase})" if a.fase else ""
    titulo(f"GMD por animal{fase_str}")
    dados = []
    for r in rows:
        dias = (datetime.fromisoformat(r["fim"]) - datetime.fromisoformat(r["inicio"])).days
        gmd = (r["peso_fim"] - r["peso_ini"]) / dias if dias > 0 else 0
        dados.append([r["brinco"], r["categoria"], r["peso_ini"], r["peso_fim"],
                      f"{gmd:.3f}", dias, r["n_pesagens"]])
    if dados:
        tabela(["Brinco","Categoria","Peso Ini","Peso Fim","GMD (kg/d)","Dias","Pesagens"],
               dados, [10,10,9,9,11,6,9])
    conn.close()

def cmd_relatorio_prenhez(a):
    conn = get_db()
    total_f = conn.execute("SELECT COUNT(*) as n FROM animal WHERE sexo='F' AND status='Ativo'").fetchone()["n"]
    prenhes = conn.execute("""SELECT COUNT(*) as n FROM reproducao
        WHERE resultado_dg='Positivo' AND data_parto_real IS NULL""").fetchone()["n"]
    partos = conn.execute("SELECT COUNT(*) as n FROM reproducao WHERE data_parto_real IS NOT NULL").fetchone()["n"]
    mortalidade = conn.execute("SELECT COUNT(*) as n FROM mortalidade").fetchone()["n"]
    titulo("Relatório Reprodutivo")
    dados = [
        ["Fêmeas ativas", total_f],
        ["Prenhas (DG+)", prenhes],
        ["Partos realizados", partos],
        ["Mortalidade total", mortalidade],
    ]
    if total_f > 0:
        dados.append(["Taxa de prenhez (%)", f"{prenhes/total_f*100:.1f}%"])
    tabela(["Indicador","Valor"], dados)
    conn.close()

def cmd_relatorio_financeiro(a):
    conn = get_db()
    titulo("Relatório Financeiro")
    compras = conn.execute("SELECT COUNT(*) as n, SUM(valor_total) as total FROM movimentacao WHERE tipo='Compra'").fetchone()
    vendas  = conn.execute("SELECT COUNT(*) as n, SUM(valor_total) as total FROM movimentacao WHERE tipo='Venda'").fetchone()
    c_tot = compras["total"] or 0
    v_tot = vendas["total"] or 0
    dados = [
        ["Compras (qtd)", compras["n"]],
        ["Compras (R$)", f"R$ {c_tot:,.2f}"],
        ["Vendas (qtd)", vendas["n"]],
        ["Vendas (R$)", f"R$ {v_tot:,.2f}"],
        ["Saldo (R$)", f"R$ {v_tot - c_tot:,.2f}"],
    ]
    tabela(["Indicador","Valor"], dados)
    conn.close()

# ─────────────────────────────────────────────────────
# PARSER PRINCIPAL
# ─────────────────────────────────────────────────────
def build_parser():
    p = argparse.ArgumentParser(
        prog="gado",
        description=cor("🐄  Sistema de Gerenciamento de Gado", BOLD),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{cor("Exemplos:", BOLD)}
  gado animal add --brinco 001 --sexo F --categoria Vaca --raca Nelore
  gado animal list --status Ativo
  gado animal show --brinco 001
  gado animal baixa --brinco 001 --tipo venda --peso 480 --valor-arroba 320 --comprador "Frigorífico X"
  gado lote add --nome "Engorda-A" --fase Engorda --pasto "Pasto Norte"
  gado lote add-animal --lote "Engorda-A" --brinco 001
  gado pesagem add --brinco 001 --peso 350 --fase Recria
  gado pesagem lote --lote "Engorda-A" --fase Engorda
  gado repro add --femea 010 --touro 002 --tipo IATF --data 2024-03-01
  gado repro dg --femea 010 --resultado Positivo --parto-previsto 2024-12-10
  gado sanidade add --lote "Engorda-A" --tipo Vacina --produto "Febre Aftosa"
  gado relatorio rebanho
  gado relatorio gmd --fase Engorda
"""
    )
    sub = p.add_subparsers(dest="cmd", title="Módulos")

    # ── ANIMAL ──────────────────────────────
    pa = sub.add_parser("animal", help="Gestão de animais")
    sa = pa.add_subparsers(dest="sub")

    s = sa.add_parser("add", help="Cadastrar animal")
    s.add_argument("--brinco", required=True)
    s.add_argument("--sexo", required=True, choices=["M","F","m","f"])
    s.add_argument("--categoria", required=True,
                   choices=["Bezerro","Bezerra","Novilho","Novilha","Vaca","Touro","Boi"])
    s.add_argument("--raca")
    s.add_argument("--nascimento")
    s.add_argument("--peso", type=float)
    s.add_argument("--mae")
    s.add_argument("--pai")
    s.add_argument("--sisbov")
    s.add_argument("--nome")
    s.add_argument("--origem", choices=["Nascido","Comprado"], default="Nascido")
    s.add_argument("--fazenda-origem", dest="fazenda_origem", help="Fazenda de origem (quando comprado)")
    s.add_argument("--obs")
    # Campos de compra (usados quando --origem Comprado)
    s.add_argument("--valor-arroba", type=float, dest="valor_arroba",
                   help="Valor da arroba pago na compra (R$)")
    s.add_argument("--peso-entrada", type=float, dest="peso_entrada",
                   help="Peso no momento da compra (kg)")
    s.add_argument("--vendedor", help="Nome do vendedor")
    s.add_argument("--nf", help="Número da nota fiscal")
    s.set_defaults(func=cmd_animal_add)

    s = sa.add_parser("list", help="Listar animais")
    s.add_argument("--status", choices=["Ativo","Vendido","Morto","Descartado"])
    s.add_argument("--categoria")
    s.add_argument("--sexo")
    s.set_defaults(func=cmd_animal_list)

    s = sa.add_parser("show", help="Detalhes de um animal")
    s.add_argument("--brinco", required=True)
    s.set_defaults(func=cmd_animal_show)

    s = sa.add_parser("update", help="Atualizar animal")
    s.add_argument("--brinco", required=True)
    s.add_argument("--status", choices=["Ativo","Vendido","Morto","Descartado"])
    s.add_argument("--categoria")
    s.add_argument("--nome")
    s.add_argument("--raca")
    s.add_argument("--sisbov")
    s.add_argument("--origem", choices=["Nascido","Comprado"])
    s.add_argument("--fazenda-origem", dest="fazenda_origem", help="Fazenda de origem")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_animal_update)

    s = sa.add_parser("delete", help="Deletar animal cadastrado incorretamente")
    s.add_argument("--brinco", required=True)
    s.add_argument("--force", action="store_true", help="Força deleção mesmo com registros vinculados")
    s.set_defaults(func=cmd_animal_delete)

    s = sa.add_parser("baixa", help="Registrar saída (venda/morte/descarte)")
    s.add_argument("--brinco", required=True)
    s.add_argument("--tipo", required=True, choices=["venda","morte","descarte"])
    s.add_argument("--peso", type=float)
    s.add_argument("--valor-arroba", type=float, dest="valor_arroba")
    s.add_argument("--comprador")
    s.add_argument("--nf")
    s.add_argument("--causa")
    s.add_argument("--laudo")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_animal_baixa)

    # ── PASTO ───────────────────────────────
    pp = sub.add_parser("pasto", help="Gestão de pastos")
    sp = pp.add_subparsers(dest="sub")

    s = sp.add_parser("add", help="Cadastrar pasto")
    s.add_argument("--nome", required=True)
    s.add_argument("--area", type=float)
    s.add_argument("--forrageira")
    s.add_argument("--capacidade", type=int)
    s.add_argument("--obs")
    s.set_defaults(func=cmd_pasto_add)

    s = sp.add_parser("list", help="Listar pastos")
    s.set_defaults(func=cmd_pasto_list)

    # ── LOTE ────────────────────────────────
    pl = sub.add_parser("lote", help="Gestão de lotes")
    sl = pl.add_subparsers(dest="sub")

    s = sl.add_parser("add", help="Criar lote")
    s.add_argument("--nome", required=True)
    s.add_argument("--fase", required=True, choices=["Cria","Recria","Engorda"])
    s.add_argument("--pasto")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_lote_add)

    s = sl.add_parser("list", help="Listar lotes")
    s.set_defaults(func=cmd_lote_list)

    s = sl.add_parser("show", help="Ver animais do lote")
    s.add_argument("--nome", required=True)
    s.set_defaults(func=cmd_lote_show)

    s = sl.add_parser("add-animal", help="Adicionar animal ao lote")
    s.add_argument("--lote", required=True)
    s.add_argument("--brinco", required=True)
    s.set_defaults(func=cmd_lote_adicionar_animal)

    # ── PESAGEM ─────────────────────────────
    pw = sub.add_parser("pesagem", help="Registro de pesagens")
    sw = pw.add_subparsers(dest="sub")

    s = sw.add_parser("add", help="Registrar pesagem individual")
    s.add_argument("--brinco", required=True)
    s.add_argument("--peso", type=float, required=True)
    s.add_argument("--fase", choices=["Cria","Recria","Engorda"])
    s.add_argument("--data")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_pesagem_add)

    s = sw.add_parser("lote", help="Pesagem interativa de lote")
    s.add_argument("--lote", required=True)
    s.add_argument("--fase", choices=["Cria","Recria","Engorda"])
    s.add_argument("--data")
    s.set_defaults(func=cmd_pesagem_lote)

    s = sw.add_parser("historico", help="Histórico de pesagens")
    s.add_argument("--brinco", required=True)
    s.set_defaults(func=cmd_pesagem_historico)

    # ── REPRODUÇÃO ──────────────────────────
    pr = sub.add_parser("repro", help="Gestão reprodutiva")
    sr = pr.add_subparsers(dest="sub")

    s = sr.add_parser("add", help="Registrar cobertura")
    s.add_argument("--femea", required=True)
    s.add_argument("--touro")
    s.add_argument("--tipo", choices=["Monta Natural","IA","IATF"], default="Monta Natural")
    s.add_argument("--data")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_repro_add)

    s = sr.add_parser("dg", help="Registrar diagnóstico de gestação")
    s.add_argument("--femea", required=True)
    s.add_argument("--resultado", choices=["Positivo","Negativo","Vazia"], required=True)
    s.add_argument("--data")
    s.add_argument("--parto-previsto", dest="parto_previsto")
    s.set_defaults(func=cmd_repro_dg)

    s = sr.add_parser("parto", help="Registrar parto")
    s.add_argument("--femea", required=True)
    s.add_argument("--data")
    s.add_argument("--cria")
    s.set_defaults(func=cmd_repro_parto)

    s = sr.add_parser("list", help="Listar coberturas")
    s.set_defaults(func=cmd_repro_list)

    # ── SANIDADE ────────────────────────────
    ps = sub.add_parser("sanidade", help="Manejo sanitário")
    ss = ps.add_subparsers(dest="sub")

    s = ss.add_parser("add", help="Registrar procedimento sanitário")
    s.add_argument("--brinco")
    s.add_argument("--lote")
    s.add_argument("--tipo", required=True, choices=["Vacina","Vermífugo","Carrapaticida","Exame","Outro"])
    s.add_argument("--produto", required=True)
    s.add_argument("--dose", type=float)
    s.add_argument("--lote-produto", dest="lote_produto")
    s.add_argument("--responsavel")
    s.add_argument("--data")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_sanidade_add)

    s = ss.add_parser("list", help="Histórico sanitário")
    s.set_defaults(func=cmd_sanidade_list)

    # ── RELATÓRIOS ──────────────────────────

    # ── MOVIMENTAÇÃO ────────────────────────────
    pm = sub.add_parser("mov", help="Movimentações financeiras (compra/venda)")
    sm = pm.add_subparsers(dest="sub")

    s = sm.add_parser("list", help="Listar movimentações")
    s.add_argument("--brinco")
    s.add_argument("--tipo", choices=["Compra","Venda"])
    s.set_defaults(func=cmd_mov_list)

    s = sm.add_parser("add", help="Registrar movimentação avulsa")
    s.add_argument("--brinco", required=True)
    s.add_argument("--tipo", required=True, choices=["Compra","Venda"])
    s.add_argument("--peso", type=float)
    s.add_argument("--valor-arroba", type=float, dest="valor_arroba")
    s.add_argument("--data")
    s.add_argument("--contraparte")
    s.add_argument("--nf")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_mov_add)

    s = sm.add_parser("update", help="Editar movimentação pelo ID")
    s.add_argument("--id", type=int, required=True, help="ID da movimentação (use 'gado mov list' para ver)")
    s.add_argument("--peso", type=float)
    s.add_argument("--valor-arroba", type=float, dest="valor_arroba")
    s.add_argument("--data")
    s.add_argument("--contraparte")
    s.add_argument("--nf")
    s.add_argument("--obs")
    s.set_defaults(func=cmd_mov_update)

    s = sm.add_parser("delete", help="Deletar movimentação pelo ID")
    s.add_argument("--id", type=int, required=True)
    s.set_defaults(func=cmd_mov_delete)
    prp = sub.add_parser("relatorio", help="Relatórios e indicadores")
    srp = prp.add_subparsers(dest="sub")

    s = srp.add_parser("rebanho", help="Resumo do rebanho")
    s.set_defaults(func=cmd_relatorio_rebanho)

    s = srp.add_parser("gmd", help="Ganho médio diário por animal")
    s.add_argument("--fase", choices=["Cria","Recria","Engorda"])
    s.set_defaults(func=cmd_relatorio_gmd)

    s = srp.add_parser("prenhez", help="Indicadores reprodutivos")
    s.set_defaults(func=cmd_relatorio_prenhez)

    s = srp.add_parser("financeiro", help="Resumo financeiro")
    s.set_defaults(func=cmd_relatorio_financeiro)

    return p

# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────
def main():
    init_db()
    parser = build_parser()
    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        return

    # Verifica subcomando
    sub_attr = getattr(args, "sub", None)
    if not sub_attr:
        # mostra help do subcomando
        for action in parser._subparsers._actions:
            if hasattr(action, '_name_parser_map') and args.cmd in action._name_parser_map:
                action._name_parser_map[args.cmd].print_help()
                return

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
