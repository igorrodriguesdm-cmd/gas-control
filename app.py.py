import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Banco de dados em memória simulado para a rede de depósitos
DATABASE = {
    "usuarios": [
        {"id": 1, "usuario": "admin", "senha": "123", "tipo": "admin", "nome": "Administrador Geral"},
        {"id": 2, "usuario": "dep1", "senha": "123", "tipo": "deposito", "deposito_id": 1, "nome": "Depósito Centro"},
        {"id": 3, "usuario": "dep2", "senha": "123", "tipo": "deposito", "deposito_id": 2, "nome": "Depósito Zona Sul"}
    ],
    "depositos": {
        1: {"id": 1, "nome": "Depósito Centro", "cheias": 150, "vazias": 40, "defeito": 5},
        2: {"id": 2, "nome": "Depósito Zona Sul", "cheias": 90, "vazias": 25, "defeito": 2}
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
    
    return jsonify({"erro": "Credenciais inválidas. Verifique usuário e senha."}), 401

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
        "historico": DATABASE["historico"][-10:] # Últimas 10 movimentações
    }), 200

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

    dep = DATABASE["depositos"].get(dep_id)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado."}), 404
    
    if qtd <= 0:
        return jsonify({"erro": "Quantidade inválida para venda."}), 400
        
    if dep["cheias"] < qtd:
        return jsonify({"erro": f"Estoque insuficiente! Disponível: {dep['cheias']} botijões cheios."}), 400

    dep["cheias"] -= qtd
    dep["vazias"] += qtd
    
    DATABASE["historico"].append({
        "tipo": "Venda",
        "deposito": dep["nome"],
        "quantidade": qtd,
        "status": "Cheia -> Vazia"
    })

    return jsonify({"mensagem": "Venda realizada com sucesso!", "deposito": dep}), 200

@app.route('/api/entrada-carreta', methods=['POST'])
def entrada_carreta():
    data = request.get_json() or {}
    dep_id = data.get('deposito_id')
    qtd = int(data.get('quantidade', 0))

    dep = DATABASE["depositos"].get(dep_id)
    if not dep:
        return jsonify({"erro": "Depósito não encontrado."}), 404

    if qtd <= 0:
        return jsonify({"erro": "Quantidade inválida para entrada."}), 400

    dep["cheias"] += qtd
    
    DATABASE["historico"].append({
        "tipo": "Carreta (Cheias)",
        "deposito": dep["nome"],
        "quantidade": qtd,
        "status": "Entrada de Carga"
    })

    return jsonify({"mensagem": "Entrada de carreta registrada com sucesso!", "deposito": dep}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)