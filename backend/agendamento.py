import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "agendamento.db")

STATUS_VALIDOS = {"AGENDADO", "CANCELADO", "CONCLUIDO"}

app = Flask(__name__)

def get_db():
    if "db" not in g:
        conectar = sqlite3.connect(DB_PATH)
        conectar.row_factory = sqlite3.Row
        conectar.execute("PRAGMA foreign_keys = ON;")
        g.db = conectar
    return g.db

def get_connection():
    conectar = sqlite3.connect(DB_PATH)
    conectar.row_factory = sqlite3.Row
    conectar.execute("PRAGMA foreign_keys = ON;")
    return conectar

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def create_tables(conectar):
    conectar.executescript("""
    CREATE TABLE IF NOT EXISTS administradores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        senha_hash TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'ADMIN'
    );

    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        telefone TEXT NOT NULL,
        observacoes TEXT
    );

    CREATE TABLE IF NOT EXISTS servicos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        duracao_minutos INTEGER NOT NULL CHECK (duracao_minutos > 0),
        preco REAL,
        ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1))
    );

    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        servico_id INTEGER NOT NULL,
        administrador_id INTEGER NOT NULL,
        data_atendimento TEXT NOT NULL,
        horario_atendimento TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'AGENDADO',
        observacoes TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT,
        FOREIGN KEY (servico_id) REFERENCES servicos(id) ON DELETE RESTRICT,
        FOREIGN KEY (administrador_id) REFERENCES administradores(id) ON DELETE RESTRICT,
        CHECK (status IN ('AGENDADO', 'CANCELADO', 'CONCLUIDO'))
    );
    """)
    conectar.commit()

def ensure_default_admin(conectar):
    row = conectar.execute("SELECT id FROM administradores LIMIT 1").fetchone()
    if not row:
        conectar.execute("""
            INSERT INTO administradores (nome, email, senha_hash, perfil)
            VALUES (?, ?, ?, ?)
        """, ("Administrador Padrão", "admin@local.com", "123456", "ADMIN"))
        conectar.commit()

def setup_database():
    conectar = get_connection()
    try:
        create_tables(conectar)
        ensure_default_admin(conectar)
    finally:
        conectar.close()

def row_to_dict(row):
    return dict(row) if row else None

def json_error(message, status_code=400, extra=None):
    payload = {"erro": message}
    if extra is not None:
        payload["detalhes"] = extra
    return jsonify(payload), status_code

def parse_json_body():
    data = request.get_json(silent=True)
    if data is None:
        return None, json_error("Body JSON inválido ou ausente.", 400)
    return data, None

def validar_data(data_str):
    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return True
    except Exception:
        return False

def validar_hora(hora_str):
    try:
        datetime.strptime(hora_str, "%H:%M")
        return True
    except Exception:
        return False

def status_normalizado(valor):
    if valor is None:
        return None
    return str(valor).strip().upper()

def buscar_servico(conectar, servico_id):
    return conectar.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()


def buscar_cliente(conectar, cliente_id):
    return conectar.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()

def buscar_admin(conectar, admin_id):
    return conectar.execute("SELECT * FROM administradores WHERE id = ?", (admin_id,)).fetchone()

def buscar_agendamento(conectar, agendamento_id):
    return conectar.execute("""
        SELECT
            a.*,
            c.nome AS cliente_nome,
            c.telefone AS cliente_telefone,
            s.nome AS servico_nome,
            s.duracao_minutos,
            s.preco,
            adm.nome AS administrador_nome
        FROM agendamentos a
        JOIN clientes c ON c.id = a.cliente_id
        JOIN servicos s ON s.id = a.servico_id
        JOIN administradores adm ON adm.id = a.administrador_id
        WHERE a.id = ?
    """, (agendamento_id,)).fetchone()

def intervalo_agendamento(data_atendimento, horario_atendimento, duracao_minutos):
    inicio = datetime.strptime(f"{data_atendimento} {horario_atendimento}", "%Y-%m-%d %H:%M")
    fim = inicio + timedelta(minutes=int(duracao_minutos))
    return inicio, fim

def verificar_conflito(conectar, data_atendimento, horario_atendimento, servico_id, ignorar_agendamento_id=None):
    servico = buscar_servico(conectar, servico_id)
    if not servico:
        return {"conflito": False, "motivo": "Serviço não encontrado."}

    novo_inicio, novo_fim = intervalo_agendamento(
        data_atendimento,
        horario_atendimento,
        servico["duracao_minutos"]
    )

    query = """
        SELECT
            a.id,
            a.data_atendimento,
            a.horario_atendimento,
            a.status,
            a.cliente_id,
            c.nome AS cliente_nome,
            a.servico_id,
            s.nome AS servico_nome,
            s.duracao_minutos
        FROM agendamentos a
        JOIN servicos s ON s.id = a.servico_id
        JOIN clientes c ON c.id = a.cliente_id
        WHERE a.data_atendimento = ?
          AND a.status != 'CANCELADO'
    """
    params = [data_atendimento]

    if ignorar_agendamento_id is not None:
        query += " AND a.id != ?"
        params.append(ignorar_agendamento_id)

    existentes = conectar.execute(query, tuple(params)).fetchall()

    for ag in existentes:
        existente_inicio, existente_fim = intervalo_agendamento(
            ag["data_atendimento"],
            ag["horario_atendimento"],
            ag["duracao_minutos"]
        )

        if novo_inicio < existente_fim and novo_fim > existente_inicio:
            return {
                "conflito": True,
                "agendamento_existente": {
                    "id": ag["id"],
                    "cliente_nome": ag["cliente_nome"],
                    "servico_nome": ag["servico_nome"],
                    "horario_inicio": ag["horario_atendimento"],
                    "horario_fim": existente_fim.strftime("%H:%M"),
                    "status": ag["status"]
                }
            }

    return {"conflito": False}

def listar_agendamentos_query(conectar, filtros=None):
    filtros = filtros or {}
    query = """
        SELECT
            a.id,
            a.data_atendimento,
            a.horario_atendimento,
            a.status,
            a.observacoes,
            a.cliente_id,
            c.nome AS cliente_nome,
            c.telefone AS cliente_telefone,
            a.servico_id,
            s.nome AS servico_nome,
            s.duracao_minutos,
            s.preco,
            a.administrador_id,
            adm.nome AS administrador_nome
        FROM agendamentos a
        JOIN clientes c ON c.id = a.cliente_id
        JOIN servicos s ON s.id = a.servico_id
        JOIN administradores adm ON adm.id = a.administrador_id
        WHERE 1=1
    """
    params = []

    if filtros.get("data"):
        query += " AND a.data_atendimento = ?"
        params.append(filtros["data"])

    if filtros.get("status"):
        query += " AND a.status = ?"
        params.append(filtros["status"])

    if filtros.get("cliente_id"):
        query += " AND a.cliente_id = ?"
        params.append(filtros["cliente_id"])

    if filtros.get("servico_id"):
        query += " AND a.servico_id = ?"
        params.append(filtros["servico_id"])

    query += " ORDER BY a.data_atendimento ASC, a.horario_atendimento ASC"
    return [dict(r) for r in conectar.execute(query, tuple(params)).fetchall()]

def success(message, data=None, status_code=200):
    payload = {"mensagem": message}
    if data is not None:
        payload["dados"] = data
    return jsonify(payload), status_code

# Cors
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return response

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "projeto": "Sistema Web de Agendamento de Serviços",
        "backend": "Python + Flask + SQLite",
        "status_validos": sorted(list(STATUS_VALIDOS)),
        "rotas_principais": {
            "clientes": ["/clientes", "/clientes/<id>"],
            "servicos": ["/servicos", "/servicos/<id>", "/servicos/<id>/ativo"],
            "agendamentos": [
                "/agendamentos",
                "/agendamentos/<id>",
                "/agendamentos/<id>/status"
            ]
        }
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

# Clientes
@app.route("/clientes", methods=["GET"])
def listar_clientes():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, nome, telefone, observacoes
        FROM clientes
        ORDER BY nome ASC
    """).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/clientes/<int:cliente_id>", methods=["GET"])
def obter_cliente(cliente_id):
    conn = get_db()
    row = buscar_cliente(conn, cliente_id)
    if not row:
        return json_error("Cliente não encontrado.", 404)
    return jsonify(dict(row))

@app.route("/clientes", methods=["POST"])
def criar_cliente():
    data, err = parse_json_body()
    if err:
        return err

    nome = str(data.get("nome", "")).strip()
    telefone = str(data.get("telefone", "")).strip()
    observacoes = data.get("observacoes")

    if not nome:
        return json_error("O campo 'nome' é obrigatório.")
    if not telefone:
        return json_error("O campo 'telefone' é obrigatório.")

    conectar = get_db()
    cursor = conectar.execute("""
        INSERT INTO clientes (nome, telefone, observacoes)
        VALUES (?, ?, ?)
    """, (nome, telefone, observacoes))
    conectar.commit()

    novo = buscar_cliente(conectar, cursor.lastrowid)
    return success("Cliente criado com sucesso.", dict(novo), 201)

@app.route("/clientes/<int:cliente_id>", methods=["PUT"])
def atualizar_cliente(cliente_id):
    data, err = parse_json_body()
    if err:
        return err

    conectar = get_db()
    cliente = buscar_cliente(conectar, cliente_id)
    if not cliente:
        return json_error("Cliente não encontrado.", 404)

    nome = str(data.get("nome", cliente["nome"])).strip()
    telefone = str(data.get("telefone", cliente["telefone"])).strip()
    observacoes = data.get("observacoes", cliente["observacoes"])

    if not nome:
        return json_error("O campo 'nome' é obrigatório.")
    if not telefone:
        return json_error("O campo 'telefone' é obrigatório.")

    conectar.execute("""
        UPDATE clientes
        SET nome = ?, telefone = ?, observacoes = ?
        WHERE id = ?
    """, (nome, telefone, observacoes, cliente_id))
    conectar.commit()

    atualizado = buscar_cliente(conectar, cliente_id)
    return success("Cliente atualizado com sucesso.", dict(atualizado))

@app.route("/clientes/<int:cliente_id>", methods=["DELETE"])
def deletar_cliente(cliente_id):
    conectar = get_db()
    cliente = buscar_cliente(conectar, cliente_id)
    if not cliente:
        return json_error("Cliente não encontrado.", 404)

    try:
        conectar.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conectar.commit()
    except sqlite3.IntegrityError:
        return json_error("Não é possível excluir cliente com agendamentos vinculados.", 409)

    return success("Cliente removido com sucesso.")

# Serviços
@app.route("/servicos", methods=["GET"])
def listar_servicos():
    conectar = get_db()
    ativos = request.args.get("ativos")

    query = """
        SELECT id, nome, duracao_minutos, preco, ativo
        FROM servicos
    """
    params = []

    if ativos == "1":
        query += " WHERE ativo = 1"
    elif ativos == "0":
        query += " WHERE ativo = 0"

    query += " ORDER BY nome ASC"

    rows = conectar.execute(query, tuple(params)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/servicos/<int:servico_id>", methods=["GET"])
def obter_servico(servico_id):
    conectar = get_db()
    row = buscar_servico(conectar, servico_id)
    if not row:
        return json_error("Serviço não encontrado.", 404)
    return jsonify(dict(row))

@app.route("/servicos", methods=["POST"])
def criar_servico():
    data, err = parse_json_body()
    if err:
        return err

    nome = str(data.get("nome", "")).strip()
    duracao_minutos = data.get("duracao_minutos")
    preco = data.get("preco")
    ativo = 1 if str(data.get("ativo", 1)).lower() not in ("0", "false", "não", "nao") else 0

    if not nome:
        return json_error("O campo 'nome' é obrigatório.")
    if duracao_minutos is None:
        return json_error("O campo 'duracao_minutos' é obrigatório.")

    try:
        duracao_minutos = int(duracao_minutos)
        if duracao_minutos <= 0:
            raise ValueError
    except Exception:
        return json_error("O campo 'duracao_minutos' deve ser um inteiro maior que zero.")

    if preco in ("", None):
        preco = None
    else:
        try:
            preco = float(preco)
            if preco < 0:
                return json_error("O campo 'preco' não pode ser negativo.")
        except Exception:
            return json_error("O campo 'preco' deve ser numérico.")

    conectar = get_db()
    cursor = conectar.execute("""
        INSERT INTO servicos (nome, duracao_minutos, preco, ativo)
        VALUES (?, ?, ?, ?)
    """, (nome, duracao_minutos, preco, ativo))
    conectar.commit()

    novo = buscar_servico(conectar, cursor.lastrowid)
    return success("Serviço criado com sucesso.", dict(novo), 201)

@app.route("/servicos/<int:servico_id>", methods=["PUT"])
def atualizar_servico(servico_id):
    data, err = parse_json_body()
    if err:
        return err

    conectar = get_db()
    servico = buscar_servico(conectar, servico_id)
    if not servico:
        return json_error("Serviço não encontrado.", 404)

    nome = str(data.get("nome", servico["nome"])).strip()
    duracao_minutos = data.get("duracao_minutos", servico["duracao_minutos"])
    preco = data.get("preco", servico["preco"])
    ativo = data.get("ativo", servico["ativo"])

    if not nome:
        return json_error("O campo 'nome' é obrigatório.")

    try:
        duracao_minutos = int(duracao_minutos)
        if duracao_minutos <= 0:
            raise ValueError
    except Exception:
        return json_error("O campo 'duracao_minutos' deve ser um inteiro maior que zero.")

    if preco in ("", None):
        preco = None
    else:
        try:
            preco = float(preco)
            if preco < 0:
                return json_error("O campo 'preco' não pode ser negativo.")
        except Exception:
            return json_error("O campo 'preco' deve ser numérico.")

    ativo = 1 if str(ativo).lower() not in ("0", "false", "não", "nao") else 0

    cursor = conectar.execute("""
        UPDATE servicos
        SET nome = ?, duracao_minutos = ?, preco = ?, ativo = ?
        WHERE id = ?
    """, (nome, duracao_minutos, preco, ativo, servico_id))
    conectar.commit()

    atualizado = buscar_servico(conectar, servico_id)
    return success("Serviço atualizado com sucesso.", dict(atualizado))

@app.route("/servicos/<int:servico_id>/ativo", methods=["PATCH"])
def alterar_status_ativo_servico(servico_id):
    data, err = parse_json_body()
    if err:
        return err

    if "ativo" not in data:
        return json_error("O campo 'ativo' é obrigatório.")

    conectar = get_db()
    servico = buscar_servico(conectar, servico_id)
    if not servico:
        return json_error("Serviço não encontrado.", 404)

    ativo = 1 if str(data["ativo"]).lower() not in ("0", "false", "não", "nao") else 0
    conectar.execute("UPDATE servicos SET ativo = ? WHERE id = ?", (ativo, servico_id))
    conectar.commit()

    atualizado = buscar_servico(conectar, servico_id)
    return success("Status do serviço atualizado com sucesso.", dict(atualizado))

@app.route("/servicos/<int:servico_id>", methods=["DELETE"])
def deletar_servico(servico_id):
    conectar = get_db()
    servico = buscar_servico(conectar, servico_id)
    if not servico:
        return json_error("Serviço não encontrado.", 404)

    try:
        conectar.execute("DELETE FROM servicos WHERE id = ?", (servico_id,))
        conectar.commit()
    except sqlite3.IntegrityError:
        return json_error("Não é possível excluir serviço com agendamentos vinculados.", 409)

    return success("Serviço removido com sucesso.")

@app.route("/agendamentos", methods=["GET"])
def listar_agendamentos():
    conectar = get_db()
    filtros = {
        "data": request.args.get("data"),
        "status": status_normalizado(request.args.get("status")),
        "cliente_id": request.args.get("cliente_id"),
        "servico_id": request.args.get("servico_id"),
    }

    if filtros["data"] and not validar_data(filtros["data"]):
        return json_error("Parâmetro 'data' inválido. Use YYYY-MM-DD.")

    if filtros["status"] and filtros["status"] not in STATUS_VALIDOS:
        return json_error("Parâmetro 'status' inválido.")

    rows = listar_agendamentos_query(conectar, filtros)
    return jsonify(rows)

@app.route("/agendamentos/<int:agendamento_id>", methods=["GET"])
def obter_agendamento(agendamento_id):
    conectar = get_db()
    row = buscar_agendamento(conectar, agendamento_id)
    if not row:
        return json_error("Agendamento não encontrado.", 404)
    return jsonify(dict(row))

@app.route("/agendamentos", methods=["POST"])
def criar_agendamento():
    data, err = parse_json_body()
    if err:
        return err

    cliente_id = data.get("cliente_id")
    servico_id = data.get("servico_id")
    administrador_id = data.get("administrador_id", 1)
    data_atendimento = data.get("data_atendimento")
    horario_atendimento = data.get("horario_atendimento")
    observacoes = data.get("observacoes")

    if cliente_id is None:
        return json_error("O campo 'cliente_id' é obrigatório.")
    if servico_id is None:
        return json_error("O campo 'servico_id' é obrigatório.")
    if not data_atendimento:
        return json_error("O campo 'data_atendimento' é obrigatório.")
    if not horario_atendimento:
        return json_error("O campo 'horario_atendimento' é obrigatório.")

    try:
        cliente_id = int(cliente_id)
        servico_id = int(servico_id)
        administrador_id = int(administrador_id)
    except Exception:
        return json_error("IDs devem ser numéricos.")

    if not validar_data(data_atendimento):
        return json_error("Data inválida. Use YYYY-MM-DD.")
    if not validar_hora(horario_atendimento):
        return json_error("Horário inválido. Use HH:MM.")

    conectar = get_db()

    cliente = buscar_cliente(conectar, cliente_id)
    if not cliente:
        return json_error("Cliente não encontrado.", 404)

    servico = buscar_servico(conectar, servico_id)
    if not servico:
        return json_error("Serviço não encontrado.", 404)

    if int(servico["ativo"]) != 1:
        return json_error("Não é possível agendar um serviço inativo.", 409)

    admin = buscar_admin(conectar, administrador_id)
    if not admin:
        return json_error("Administrador não encontrado.", 404)

    conflito = verificar_conflito(conectar, data_atendimento, horario_atendimento, servico_id)
    if conflito.get("conflito"):
        return json_error("Conflito de horário detectado.", 409, conflito["agendamento_existente"])

    cursor = conectar.execute("""
        INSERT INTO agendamentos (
            cliente_id, servico_id, administrador_id,
            data_atendimento, horario_atendimento, status, observacoes
        )
        VALUES (?, ?, ?, ?, ?, 'AGENDADO', ?)
    """, (
        cliente_id, servico_id, administrador_id,
        data_atendimento, horario_atendimento, observacoes
    ))
    conectar.commit()

    novo = buscar_agendamento(conectar, cursor.lastrowid)
    return success("Agendamento criado com sucesso.", dict(novo), 201)

@app.route("/agendamentos/<int:agendamento_id>", methods=["PUT"])
def atualizar_agendamento(agendamento_id):
    data, err = parse_json_body()
    if err:
        return err

    conectar = get_db()
    atual = conectar.execute("SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,)).fetchone()
    if not atual:
        return json_error("Agendamento não encontrado.", 404)

    cliente_id = data.get("cliente_id", atual["cliente_id"])
    servico_id = data.get("servico_id", atual["servico_id"])
    administrador_id = data.get("administrador_id", atual["administrador_id"])
    data_atendimento = data.get("data_atendimento", atual["data_atendimento"])
    horario_atendimento = data.get("horario_atendimento", atual["horario_atendimento"])
    observacoes = data.get("observacoes", atual["observacoes"])
    status = status_normalizado(data.get("status", atual["status"]))

    try:
        cliente_id = int(cliente_id)
        servico_id = int(servico_id)
        administrador_id = int(administrador_id)
    except Exception:
        return json_error("IDs devem ser numéricos.")

    if not validar_data(data_atendimento):
        return json_error("Data inválida. Use YYYY-MM-DD.")
    if not validar_hora(horario_atendimento):
        return json_error("Horário inválido. Use HH:MM.")
    if status not in STATUS_VALIDOS:
        return json_error("Status inválido.")

    cliente = buscar_cliente(conectar, cliente_id)
    if not cliente:
        return json_error("Cliente não encontrado.", 404)

    servico = buscar_servico(conectar, servico_id)
    if not servico:
        return json_error("Serviço não encontrado.", 404)

    if int(servico["ativo"]) != 1:
        return json_error("Não é possível usar um serviço inativo no agendamento.", 409)

    admin = buscar_admin(conectar, administrador_id)
    if not admin:
        return json_error("Administrador não encontrado.", 404)

    if status != "CANCELADO":
        conflito = verificar_conflito(
            conectar,
            data_atendimento,
            horario_atendimento,
            servico_id,
            ignorar_agendamento_id=agendamento_id
        )
        if conflito.get("conflito"):
            return json_error("Conflito de horário detectado.", 409, conflito["agendamento_existente"])

    conectar.execute("""
        UPDATE agendamentos
        SET cliente_id = ?,
            servico_id = ?,
            administrador_id = ?,
            data_atendimento = ?,
            horario_atendimento = ?,
            status = ?,
            observacoes = ?
        WHERE id = ?
    """, (
        cliente_id,
        servico_id,
        administrador_id,
        data_atendimento,
        horario_atendimento,
        status,
        observacoes,
        agendamento_id
    ))
    conectar.commit()

    atualizado = buscar_agendamento(conectar, agendamento_id)
    return success("Agendamento atualizado com sucesso.", dict(atualizado))


@app.route("/agendamentos/<int:agendamento_id>/status", methods=["PATCH"])
def alterar_status_agendamento(agendamento_id):
    data, err = parse_json_body()
    if err:
        return err

    novo_status = status_normalizado(data.get("status"))
    if not novo_status:
        return json_error("O campo 'status' é obrigatório.")
    if novo_status not in STATUS_VALIDOS:
        return json_error(f"Status inválido. Use um destes: {', '.join(sorted(STATUS_VALIDOS))}")

    conectar = get_db()
    agendamento = conectar.execute("SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,)).fetchone()
    if not agendamento:
        return json_error("Agendamento não encontrado.", 404)

    conectar.execute("""
        UPDATE agendamentos
        SET status = ?
        WHERE id = ?
    """, (novo_status, agendamento_id))
    conectar.commit()

    atualizado = buscar_agendamento(conectar, agendamento_id)
    return success("Status do agendamento atualizado com sucesso.", dict(atualizado))

@app.route("/agendamentos/<int:agendamento_id>", methods=["DELETE"])
def deletar_agendamento(agendamento_id):
    conectar = get_db()
    agendamento = conectar.execute("SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,)).fetchone()
    if not agendamento:
        return json_error("Agendamento não encontrado.", 404)

    conectar.execute("DELETE FROM agendamentos WHERE id = ?", (agendamento_id,))
    conectar.commit()

    return success("Agendamento removido com sucesso.")

@app.route("/administradores", methods=["GET"])
def listar_administradores():
    conectar = get_db()
    rows = conectar.execute("""
        SELECT id, nome, email, perfil
        FROM administradores
        ORDER BY nome ASC
    """).fetchall()
    return jsonify([dict(r) for r in rows])

def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cli_initdb():
    conectar = get_connection()
    try:
        create_tables(conectar)
        ensure_default_admin(conectar)
        print("Banco inicializado com sucesso.")
        print(f"Arquivo do banco: {DB_PATH}")
    finally:
        conectar.close()

def cli_seed():
    conectar = get_connection()
    try:
        create_tables(conectar)
        ensure_default_admin(conectar)

        conectar.execute("""
            INSERT INTO clientes (nome, telefone, observacoes)
            SELECT ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM clientes WHERE telefone = ?)
        """, ("João Silva", "11999990001", "Cliente de teste", "11999990001"))

        conectar.execute("""
            INSERT INTO clientes (nome, telefone, observacoes)
            SELECT ?, ?, ?
            WHERE NOT EXISTS (SELECT 1 FROM clientes WHERE telefone = ?)
        """, ("Maria Souza", "11999990002", "Prefere horário da manhã", "11999990002"))

        conectar.execute("""
            INSERT INTO servicos (nome, duracao_minutos, preco, ativo)
            SELECT ?, ?, ?, 1
            WHERE NOT EXISTS (SELECT 1 FROM servicos WHERE nome = ?)
        """, ("Corte de Cabelo", 45, 35.0, "Corte de Cabelo"))

        conectar.execute("""
            INSERT INTO servicos (nome, duracao_minutos, preco, ativo)
            SELECT ?, ?, ?, 1
            WHERE NOT EXISTS (SELECT 1 FROM servicos WHERE nome = ?)
        """, ("Manicure", 60, 50.0, "Manicure"))

        conectar.commit()
        print("Dados de exemplo inseridos com sucesso.")
    finally:
        conectar.close()

def cli_listar_clientes():
    conectar = get_connection()
    try:
        rows = conectar.execute("SELECT * FROM clientes ORDER BY nome ASC").fetchall()
        print_json([dict(r) for r in rows])
    finally:
        conectar.close()

def cli_criar_cliente(args):
    if len(args) < 2:
        print("Uso: python app.py criar-cliente \"Nome\" \"Telefone\" [observacoes]")
        return
    nome = args[0]
    telefone = args[1]
    observacoes = args[2] if len(args) > 2 else None

    conectar = get_connection()
    try:
        cursor = conectar.execute("""
            INSERT INTO clientes (nome, telefone, observacoes)
            VALUES (?, ?, ?)
        """, (nome, telefone, observacoes))
        conectar.commit()
        row = conectar.execute("SELECT * FROM clientes WHERE id = ?", (cursor.lastrowid,)).fetchone()
        print_json(dict(row))
    finally:
        conectar.close()

def cli_listar_servicos():
    conectar = get_connection()
    try:
        rows = conectar.execute("SELECT * FROM servicos ORDER BY nome ASC").fetchall()
        print_json([dict(r) for r in rows])
    finally:
        conectar.close()

def cli_criar_servico(args):
    if len(args) < 2:
        print("Uso: python app.py criar-servico \"Nome\" duracao_minutos [preco]")
        return

    nome = args[0]
    try:
        duracao = int(args[1])
    except Exception:
        print("duracao_minutos deve ser inteiro.")
        return

    preco = None
    if len(args) > 2:
        try:
            preco = float(args[2])
        except Exception:
            print("preco deve ser numérico.")
            return

    conectar = get_connection()
    try:
        cursor = conectar.execute("""
            INSERT INTO servicos (nome, duracao_minutos, preco, ativo)
            VALUES (?, ?, ?, 1)
        """, (nome, duracao, preco))
        conectar.commit()
        row = conectar.execute("SELECT * FROM servicos WHERE id = ?", (cursor.lastrowid,)).fetchone()
        print_json(dict(row))
    finally:
        conectar.close()

def cli_listar_agendamentos(filtro_data=None):
    conectar = get_connection()
    try:
        filtros = {}
        if filtro_data:
            filtros["data"] = filtro_data
        rows = listar_agendamentos_query(conectar, filtros)
        print_json(rows)
    finally:
        conectar.close()

def cli_criar_agendamento(args):
    if len(args) < 4:
        print("Uso: python app.py criar-agendamento cliente_id servico_id YYYY-MM-DD HH:MM [observacoes]")
        return

    try:
        cliente_id = int(args[0])
        servico_id = int(args[1])
    except Exception:
        print("cliente_id e servico_id devem ser inteiros.")
        return

    data_atendimento = args[2]
    horario_atendimento = args[3]
    observacoes = args[4] if len(args) > 4 else None

    if not validar_data(data_atendimento):
        print("Data inválida. Use YYYY-MM-DD.")
        return

    if not validar_hora(horario_atendimento):
        print("Horário inválido. Use HH:MM.")
        return

    conectar = get_connection()
    try:
        create_tables(conectar)
        ensure_default_admin(conectar)

        cliente = buscar_cliente(conectar, cliente_id)
        servico = buscar_servico(conectar, servico_id)

        if not cliente:
            print("Cliente não encontrado.")
            return
        if not servico:
            print("Serviço não encontrado.")
            return
        if int(servico["ativo"]) != 1:
            print("Serviço inativo.")
            return

        conflito = verificar_conflito(conectar, data_atendimento, horario_atendimento, servico_id)
        if conflito.get("conflito"):
            print_json({
                "erro": "Conflito de horário detectado.",
                "detalhes": conflito["agendamento_existente"]
            })
            return

        cursor = conectar.execute("""
            INSERT INTO agendamentos (
                cliente_id, servico_id, administrador_id,
                data_atendimento, horario_atendimento, status, observacoes
            )
            VALUES (?, ?, 1, ?, ?, 'AGENDADO', ?)
        """, (
            cliente_id, servico_id, data_atendimento, horario_atendimento, observacoes
        ))
        conectar.commit()

        row = buscar_agendamento(conectar, cursor.lastrowid)
        print_json(dict(row))
    finally:
        conectar.close()

def cli_alterar_status(args):
    if len(args) < 2:
        print("Uso: python app.py alterar-status agendamento_id STATUS")
        return

    try:
        agendamento_id = int(args[0])
    except Exception:
        print("agendamento_id deve ser inteiro.")
        return

    status = status_normalizado(args[1])
    if status not in STATUS_VALIDOS:
        print(f"Status inválido. Use: {', '.join(sorted(STATUS_VALIDOS))}")
        return

    conectar = get_connection()
    try:
        row = conectar.execute("SELECT * FROM agendamentos WHERE id = ?", (agendamento_id,)).fetchone()
        if not row:
            print("Agendamento não encontrado.")
            return

        conectar.execute("UPDATE agendamentos SET status = ? WHERE id = ?", (status, agendamento_id))
        conectar.commit()

        atualizado = buscar_agendamento(conectar, agendamento_id)
        print_json(dict(atualizado))
    finally:
        conectar.close()

def print_help():
    print("""
Sistema de Agendamento - Backend Python
          
API:
  python app.py
  # inicia servidor em http://127.0.0.1:5000

Comandos CLI:
  python app.py initdb
  python app.py seed

  python app.py listar-clientes
  python app.py criar-cliente "Nome" "Telefone" [observacoes]

  python app.py listar-servicos
  python app.py criar-servico "Nome" duracao_minutos [preco]

  python app.py listar-agendamentos [YYYY-MM-DD]
  python app.py criar-agendamento cliente_id servico_id YYYY-MM-DD HH:MM [observacoes]
  python app.py alterar-status agendamento_id STATUS

Exemplos:
  python app.py initdb
  python app.py seed
  python app.py listar-servicos
  python app.py criar-cliente "Carlos" "11988887777" "Primeiro atendimento"
  python app.py criar-servico "Sobrancelha" 30 25
  python app.py criar-agendamento 1 1 2026-05-20 14:00 "Cliente confirmado"
  python app.py listar-agendamentos
  python app.py alterar-status 1 CONCLUIDO
""")

def run_cli():
    if len(sys.argv) == 1:
        return False 

    comando = sys.argv[1].strip().lower()
    args = sys.argv[2:]

    if comando == "initdb":
        cli_initdb()
        return True

    if comando == "seed":
        cli_seed()
        return True

    if comando == "listar-clientes":
        cli_listar_clientes()
        return True

    if comando == "criar-cliente":
        cli_criar_cliente(args)
        return True

    if comando == "listar-servicos":
        cli_listar_servicos()
        return True

    if comando == "criar-servico":
        cli_criar_servico(args)
        return True

    if comando == "listar-agendamentos":
        cli_listar_agendamentos(args[0] if args else None)
        return True

    if comando == "criar-agendamento":
        cli_criar_agendamento(args)
        return True

    if comando == "alterar-status":
        cli_alterar_status(args)
        return True

    if comando in {"help", "--help", "-h"}:
        print_help()
        return True

    print(f"Comando desconhecido: {comando}")
    print_help()
    return True

setup_database()
if __name__ == "__main__":
    executou_cli = run_cli()
    if not executou_cli:
        app.run(host="0.0.0.0", port=5000, debug=True)