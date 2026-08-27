from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Banco de dados simulado inicial
USUARIOS = [
    {"id": 1, "usuario": "admin", "senha": "123", "perfil": "adm", "deposito_id": None, "nome": "Administrador Geral"},
    {"id": 2, "usuario": "dep1", "senha": "123", "perfil": "deposito", "deposito_id": 1, "nome": "Depósito Central"},
    {"id": 3, "usuario": "dep2", "senha": "123", "perfil": "deposito", "deposito_id": 2, "nome": "Filial Norte"}
]

DEPOSITOS = [
    {"id": 1, "nome": "Depósito Central", "cheias": 150, "vazias": 40, "defeitos": 5},
    {"id": 2, "nome": "Filial Norte", "cheias": 80, "vazias": 20, "defeitos": 2}
]

HISTORICO = []

# --- AUTENTICAÇÃO ---
@app.route('/api/login', methods=['POST'])
def login():
    dados = request.json
    for u in USUARIOS:
        if u['usuario'] == dados.get('usuario') and u['senha'] == dados.get('senha'):
            return jsonify({"sucesso": True, "perfil": u['perfil'], "deposito_id": u['deposito_id'], "nome": u['nome']}), 200
    return jsonify({"sucesso": False, "erro": "Usuário ou senha inválidos!"}), 401

# --- ROTAS DO ADMIN ---
@app.route('/api/admin/depositos', methods=['GET'])
def listar_depositos_cadastrados():
    return jsonify(DEPOSITOS), 200

@app.route('/api/admin/criar-deposito', methods=['POST'])
def criar_deposito():
    dados = request.json
    novo_id = len(DEPOSITOS) + 1
    novo_dep = {
        "id": novo_id,
        "nome": dados.get('nome'),
        "cheias": int(dados.get('cheias_inicial', 0)),
        "vazias": int(dados.get('vazias_inicial', 0)),
        "defeitos": 0
    }
    DEPOSITOS.append(novo_dep)
    return jsonify({"sucesso": True, "mensagem": f"Depósito '{novo_dep['nome']}' criado com sucesso!"}), 201

@app.route('/api/admin/criar-usuario', methods=['POST'])
def criar_usuario():
    dados = request.json
    novo_id = len(USUARIOS + [1]) # garante ID único
    dep_id = dados.get('deposito_id')
    if dep_id:
        dep_id = int(dep_id)

    novo_user = {
        "id": novo_id,
        "usuario": dados.get('usuario'),
        "senha": dados.get('senha'),
        "perfil": dados.get('perfil'),
        "deposito_id": dep_id,
        "nome": dados.get('nome')
    }
    USUARIOS.append(novo_user)
    return jsonify({"sucesso": True, "mensagem": f"Usuário '{novo_user['usuario']}' criado com sucesso!"}), 201

@app.route('/api/admin/dashboard', methods=['GET'])
def dashboard_adm():
    total_cheias = sum(d['cheias'] for d in DEPOSITOS)
    total_vazias = sum(d['vazias'] for d in DEPOSITOS)
    total_defeitos = sum(d['defeitos'] for d in DEPOSITOS)
    
    vendas_hoje = sum(h['quantidade'] for h in HISTORICO if h['tipo_acao'] == 'venda' and h['data_hora'].startswith(datetime.now().strftime('%Y-%m-%d')))

    return jsonify({
        "kpis": {
            "vendas_hoje": vendas_hoje,
            "total_cheias": total_cheias,
            "total_vazias": total_vazias,
            "total_defeitos": total_defeitos
        },
        "depositos": DEPOSITOS,
        "historico": HISTORICO[::-1]
    }), 200

# --- ROTAS DO DEPÓSITO ---
@app.route('/api/estoque/<int:dep_id>', methods=['GET'])
def pegar_estoque(dep_id):
    dep = next((d for d in DEPOSITOS if d['id'] == dep_id), None)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado"}), 404
    return jsonify(dep), 200

@app.route('/api/vender', methods=['POST'])
def vender():
    dados = request.json
    dep_id = dados.get('deposito_id')
    qtd = dados.get('quantidade')
    
    dep = next((d for d in DEPOSITOS if d['id'] == dep_id), None)
    if not dep or dep['cheias'] < qtd:
        return jsonify({"erro": "Estoque de botijas cheias insuficiente!"}), 400
    
    dep['cheias'] -= qtd
    dep['vazias'] += qtd
    
    HISTORICO.append({
        "data_hora": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "origem": dep['nome'],
        "tipo_acao": "venda",
        "detalhes": f"Venda de {qtd} botijas P13 (Pgto: {dados.get('forma_pagamento')})",
        "quantidade": qtd
    })
    return jsonify({"sucesso": True, "mensagem": f"Venda de {qtd} botijas registrada!"}), 200

@app.route('/api/entrada-carreta', methods=['POST'])
def entrada_carreta():
    dados = request.json
    dep_id = dados.get('deposito_id')
    qtd = dados.get('quantidade')
    
    dep = next((d for d in DEPOSITOS if d['id'] == dep_id), None)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado"}), 404
        
    dep['cheias'] += qtd
    
    HISTORICO.append({
        "data_hora": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "origem": dep['nome'],
        "tipo_acao": "entrada_carreta",
        "detalhes": f"Recebimento Carreta - Placa/NF: {dados.get('placa')}",
        "quantidade": qtd
    })
    return jsonify({"sucesso": True, "mensagem": f"Entrada de {qtd} botijas cheias registrada!"}), 200

@app.route('/api/transferir', methods=['POST'])
def transferir():
    dados = request.json
    origem_id = dados.get('deposito_origem_id')
    destino_id = int(dados.get('deposito_destino_id'))
    tipo = dados.get('tipo_botija')
    qtd = dados.get('quantidade')
    
    dep_origem = next((d for d in DEPOSITOS if d['id'] == origem_id), None)
    dep_destino = next((d for d in DEPOSITOS if d['id'] == destino_id), None)
    
    if not dep_origem or not dep_destino:
        return jsonify({"erro": "Depósito inválido"}), 400
        
    if tipo == 'cheia':
        if dep_origem['cheias'] < qtd:
            return jsonify({"erro": "Estoque de cheias insuficiente!"}), 400
        dep_origem['cheias'] -= qtd
        dep_destino['cheias'] += qtd
    else:
        if dep_origem['vazias'] < qtd:
            return jsonify({"erro": "Estoque de vazias insuficiente!"}), 400
        dep_origem['vazias'] -= qtd
        dep_destino['vazias'] += qtd
        
    HISTORICO.append({
        "data_hora": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "origem": dep_origem['nome'],
        "tipo_acao": "transferencia",
        "detalhes": f"Enviou {qtd} botijas ({tipo}s) para {dep_destino['nome']}",
        "quantidade": qtd
    })
    return jsonify({"sucesso": True, "mensagem": f"Transferência realizada para {dep_destino['nome']}!"}), 200

@app.route('/api/registrar-defeito', methods=['POST'])
def registrar_defeito():
    dados = request.json
    dep_id = dados.get('deposito_id')
    qtd = dados.get('quantidade')
    
    dep = next((d for d in DEPOSITOS if d['id'] == dep_id), None)
    if not dep or dep['vazias'] < qtd:
        return jsonify({"erro": "Quantidade insuficiente de vazias para defeito!"}), 400
        
    dep['vazias'] -= qtd
    dep['defeitos'] += qtd
    
    HISTORICO.append({
        "data_hora": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "origem": dep['nome'],
        "tipo_acao": "defeito",
        "detalhes": f"Baixa por Avaria: {dados.get('motivo')}",
        "quantidade": qtd
    })
    return jsonify({"sucesso": True, "mensagem": f"Baixa de {qtd} unidades com defeito registrada!"}), 200

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)