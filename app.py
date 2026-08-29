import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Banco de dados simulado
DATABASE = {
    "usuarios": [
        {"id": 1, "usuario": "admin", "senha": "123", "tipo": "admin", "nome": "Administrador Geral"},
        {"id": 2, "usuario": "dep1", "senha": "123", "tipo": "deposito", "deposito_id": 1, "nome": "Depósito Centro"}
    ],
    "depositos": {
        1: {"id": 1, "nome": "Depósito Centro", "cheias": 150, "vazias": 40, "defeito": 5}
    },
    "historico": []
}

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    usuario_input = data.get('usuario')
    senha_input = data.get('senha')

    user = next((u for u in DATABASE["usuarios"] if u["usuario"] == usuario_input and u["senha"] == senha_input), None)
    
    if user:
        return jsonify({
            "id": user["id"],
            "usuario": user["usuario"],
            "tipo": user["tipo"],
            "nome": user["nome"],
            "deposito_id": user.get("deposito_id")
        }), 200
    
    return jsonify({"erro": "Credenciais inválidas."}), 401

@app.route('/api/admin/dashboard', methods=['GET'])
def admin_dashboard():
    lista_depositos = list(DATABASE["depositos"].values())
    total_cheias = sum(d["cheias"] for d in lista_depositos)
    total_vazias = sum(d["vazias"] for d in lista_depositos)
    total_defeito = sum(d["defeito"] for d in lista_depositos)
    
    return jsonify({
        "depositos": lista_depositos,
        "totais": {
            "cheias": total_cheias,
            "vazias": total_vazias,
            "defeito": total_defeito
        },
        "historico": DATABASE["historico"][-15:]
    }), 200

@app.route('/api/admin/criar-deposito', methods=['POST'])
def criar_deposito():
    data = request.get_json() or {}
    nome = data.get('nome')
    cheias_inicial = int(data.get('cheias', 0))
    usuario_login = data.get('usuario')
    senha_login = data.get('senha')

    if not nome or not usuario_login or not senha_login:
        return jsonify({"erro": "Preencha todos os campos do novo depósito."}), 400

    # Gerar novo ID de depósito
    novo_id = max(DATABASE["depositos"].keys()) + 1 if DATABASE["depositos"] else 1
    
    # Criar depósito
    DATABASE["depositos"][novo_id] = {
        "id": novo_id,
        "nome": nome,
        "cheias": cheias_inicial,
        "vazias": 0,
        "defeito": 0
    }

    # Criar usuário associado ao depósito
    novo_user_id = max(u["id"] for u in DATABASE["usuarios"]) + 1
    DATABASE["usuarios"].append({
        "id": novo_user_id,
        "usuario": usuario_login,
        "senha": senha_login,
        "tipo": "deposito",
        "deposito_id": novo_id,
        "nome": nome
    })

    return jsonify({"mensagem": f"Depósito '{nome}' cadastrado com sucesso!"}), 201

@app.route('/api/estoque/<int:deposito_id>', methods=['GET'])
def obter_estoque(deposito_id):
    dep = DATABASE["depositos"].get(deposito_id)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado."}), 404
    return jsonify(dep), 200

@app.route('/api/vender', methods=['POST'])
def registrar_venda():
    data = request.get_json() or {}
    dep_id = data.get('deposito_id')
    qtd = int(data.get('quantidade', 0))
    pagamento = data.get('pagamento', 'Dinheiro')
    tem_troca = data.get('tem_troca', True) # Se o cliente deixou vasilhame vazio

    dep = DATABASE["depositos"].get(dep_id)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado."}), 404
    
    if qtd <= 0:
        return jsonify({"erro": "Quantidade inválida."}), 400
        
    if dep["cheias"] < qtd:
        return jsonify({"erro": f"Estoque insuficiente! Disponível: {dep['cheias']} cheios."}), 400

    dep["cheias"] -= qtd
    
    # Se teve troca, entra vasilhame vazio. Se não teve troca, sai botijão cheio sem repor vazio.
    if tem_troca:
        dep["vazias"] += qtd
        status_troca = "Com Troca (Vazio entregue)"
    else:
        status_troca = "Sem Troca (Venda de vasilhame novo)"

    DATABASE["historico"].append({
        "tipo": "Venda",
        "deposito": dep["nome"],
        "quantidade": qtd,
        "status": f"Pgto: {pagamento} | {status_troca}"
    })

    return jsonify({"mensagem": "Venda registrada com sucesso!", "deposito": dep}), 200

@app.route('/api/entrada-carreta', methods=['POST'])
def entrada_carreta():
    data = request.get_json() or {}
    dep_id = data.get('deposito_id')
    qtd = int(data.get('quantidade', 0))

    dep = DATABASE["depositos"].get(dep_id)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado."}), 404

    if qtd <= 0:
        return jsonify({"erro": "Quantidade inválida."}), 400

    dep["cheias"] += qtd
    
    DATABASE["historico"].append({
        "tipo": "Carreta",
        "deposito": dep["nome"],
        "quantidade": qtd,
        "status": "Entrada de Carga Cheia"
    })

    return jsonify({"mensagem": "Carreta registrada com sucesso!", "deposito": dep}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
