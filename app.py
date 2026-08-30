from datetime import datetime
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = {
    "usuarios": [
        {
            "id": 1,
            "usuario": "admin",
            "senha": "123",
            "tipo": "admin",
            "nome": "Administrador Geral",
        },
        {
            "id": 2,
            "usuario": "dep1",
            "senha": "123",
            "tipo": "deposito",
            "deposito_id": 1,
            "nome": "Depósito Centro",
        },
    ],
    "depositos": {
        1: {
            "id": 1,
            "nome": "Depósito Centro",
            "razao_social": "Centro de Distribuição de Gas Ltda",
            "cnpj": "12.345.678/0001-99",
            "endereco": "Av. Principal, 100 - Centro",
            "cheias": 150,
            "vazias": 40,
            "defeito": 5,
            "formas_pagamento": [
                "Dinheiro",
                "PIX",
                "Cartão de Crédito",
                "Cartão de Débito",
            ],
            "caminhoes_fixos": ["ABC-1234"],
            "horario_inicio": "08:00",
            "horario_fim": "18:00",
            "tipo_fechamento": "automatico",
        }
    },
    "caminhoes": [
        {"id": 1, "placa": "ABC-1234", "capacidade": 80},
        {"id": 2, "placa": "XYZ-9876", "capacidade": 120},
    ],
    "vendas": [],
    "trocas": [],
    "movimentacoes": [],
    "fechamentos_diarios": [],
}


@app.route("/api/login", methods=["POST"])
def login():
  data = request.get_json() or {}
  usuario_input = data.get("usuario")
  senha_input = data.get("senha")
  nome_operador = data.get("nome_operador", "").strip()

  if not nome_operador:
    return (
        jsonify({
            "erro": (
                "O preenchimento do seu nome é obrigatório para auditoria."
            )
        }),
        400,
    )

  user = next(
      (
          u
          for u in DATABASE["usuarios"]
          if u["usuario"] == usuario_input and u["senha"] == senha_input
      ),
      None,
  )

  if user:
    return (
        jsonify({
            "id": user["id"],
            "usuario": user["usuario"],
            "tipo": user["tipo"],
            "nome_operador": nome_operador,
            "deposito_id": user.get("deposito_id"),
        }),
        200,
    )

  return jsonify({"erro": "Credenciais inválidas."}), 401


@app.route("/api/admin/dashboard", methods=["GET"])
def admin_dashboard():
  lista_depositos = []
  agora = datetime.now()
  hoje_str = agora.strftime("%Y-%m-%d")

  for dep_id, dep in DATABASE["depositos"].items():
    vendas_hoje = [
        v
        for v in DATABASE["vendas"]
        if v["deposito_id"] == dep_id and v["data"].startswith(hoje_str)
    ]
    total_vendas_hoje = sum(v["quantidade"] for v in vendas_hoje)
    caminhao_parado = (
        dep["caminhoes_fixos"][0] if dep["caminhoes_fixos"] else "Nenhum"
    )

    lista_depositos.append({
        "id": dep["id"],
        "nome": dep["nome"],
        "cheias": dep["cheias"],
        "vazias": dep["vazias"],
        "defeito": dep["defeito"],
        "vendas_hoje": total_vendas_hoje,
        "caminhao_parado": caminhao_parado,
        "horario": f"{dep['horario_inicio']} às {dep['horario_fim']}",
    })

  return (
      jsonify({
          "depositos": lista_depositos,
          "caminhoes": DATABASE["caminhoes"],
          "historico": DATABASE["vendas"][-15:],
      }),
      200,
  )


@app.route("/api/admin/cadastrar-tudo", methods=["POST"])
def cadastrar_tudo():
  data = request.get_json() or {}
  tipo_cadastro = data.get("tipo")

  if tipo_cadastro == "deposito":
    nome = data.get("nome")
    razao_social = data.get("razao_social", nome)
    cnpj = data.get("cnpj", "")
    endereco = data.get("endereco", "")
    cheias = int(data.get("cheias", 0))
    pagamentos = data.get("pagamentos", ["Dinheiro", "PIX"])
    caminhoes_fixos = data.get("caminhoes_fixos", [])
    horario_inicio = data.get("horario_inicio", "08:00")
    horario_fim = data.get("horario_fim", "18:00")
    tipo_fechamento = data.get("tipo_fechamento", "automatico")
    usuario_login = data.get("usuario")
    senha_login = data.get("senha")

    if not nome or not usuario_login or not senha_login:
      return (
          jsonify(
              {"erro": "Preencha os campos obrigatórios do depósito."}
          ),
          400,
      )

    novo_id = (
        max(DATABASE["depositos"].keys()) + 1 if DATABASE["depositos"] else 1
    )
    DATABASE["depositos"][novo_id] = {
        "id": novo_id,
        "nome": nome,
        "razao_social": razao_social,
        "cnpj": cnpj,
        "endereco": endereco,
        "cheias": cheias,
        "vazias": 0,
        "defeito": 0,
        "formas_pagamento": pagamentos,
        "caminhoes_fixos": caminhoes_fixos,
        "horario_inicio": horario_inicio,
        "horario_fim": horario_fim,
        "tipo_fechamento": tipo_fechamento,
    }

    novo_user_id = max(u["id"] for u in DATABASE["usuarios"]) + 1
    DATABASE["usuarios"].append({
        "id": novo_user_id,
        "usuario": usuario_login,
        "senha": senha_login,
        "tipo": "deposito",
        "deposito_id": novo_id,
        "nome": nome,
    })
    return (
        jsonify({"mensagem": f"Depósito '{nome}' cadastrado com sucesso!"}),
        201,
    )

  elif tipo_cadastro == "caminhao":
    placa = data.get("placa")
    capacidade = int(data.get("capacidade", 50))
    if not placa:
      return jsonify({"erro": "Informe a placa do caminhão."}), 400

    novo_id = max((c["id"] for c in DATABASE["caminhoes"]), default=0) + 1
    DATABASE["caminhoes"].append(
        {"id": novo_id, "placa": placa, "capacidade": capacidade}
    )
    return jsonify({"mensagem": f"Caminhão {placa} cadastrado com sucesso!"}), 201

  return jsonify({"erro": "Tipo de cadastro inválido."}), 400


@app.route("/api/admin/relatorios", methods=["POST"])
def gerar_relatorios():
  data = request.get_json() or {}
  depositos_selecionados = data.get("depositos_ids", [])
  data_inicio = data.get("data_inicio")
  data_fim = data.get("data_fim")

  vendas_filtradas = [
      v
      for v in DATABASE["vendas"]
      if (
          not depositos_selecionados
          or v["deposito_id"] in depositos_selecionados
      )
  ]

  total_gas_vendido = sum(v["quantidade"] for v in vendas_filtradas)
  faturamento_total = sum(v["valor_total"] for v in vendas_filtradas)

  pagamentos_stats = {}
  for v in vendas_filtradas:
    p = v["pagamento"]
    pagamentos_stats[p] = pagamentos_stats.get(p, 0) + v["valor_total"]

  return (
      jsonify({
          "total_gas_vendido": total_gas_vendido,
          "faturamento_total": faturamento_total,
          "por_forma_pagamento": pagamentos_stats,
          "vendas": vendas_filtradas,
      }),
      200,
  )


@app.route("/api/deposito/<int:dep_id>/dados", methods=["GET"])
def dados_deposito(dep_id):
  dep = DATABASE["depositos"].get(dep_id)
  if not dep:
    return jsonify({"erro": "Depósito não encontrado."}), 404

  hoje_str = datetime.now().strftime("%Y-%m-%d")
  vendas_hoje = [
      v
      for v in DATABASE["vendas"]
      if v["deposito_id"] == dep_id and v["data"].startswith(hoje_str)
  ]
  trocas_hoje = [
      t
      for t in DATABASE["trocas"]
      if t["deposito_id"] == dep_id and t["data"].startswith(hoje_str)
  ]

  return (
      jsonify({
          "deposito": dep,
          "caminhoes": DATABASE["caminhoes"],
          "vendas_hoje": vendas_hoje,
          "trocas_hoje": trocas_hoje,
      }),
      200,
  )


@app.route("/api/deposito/vender", methods=["POST"])
def registrar_venda_detalhada():
  data = request.get_json() or {}
  dep_id = int(data.get("deposito_id"))
  qtd = int(data.get("quantidade", 0))
  pagamento = data.get("pagamento")
  operador = data.get("operador")
  tem_troca = data.get("tem_troca", False)
  questionario = data.get("questionario", {})

  dep = DATABASE["depositos"].get(dep_id)
  if not dep:
    return jsonify({"erro": "Depósito não encontrado."}), 404

  if dep["cheias"] < qtd:
    return (
        jsonify({
            "erro": (
                f"Estoque insuficiente! Disponível: {dep['cheias']} botijões"
                " cheios."
            )
        }),
        400,
    )

  estoque_antes = dep["cheias"]
  dep["cheias"] -= qtd
  if tem_troca:
    dep["vazias"] += qtd

  estoque_depois = dep["cheias"]
  valor_unitario = 110.00
  valor_total = qtd * valor_unitario
  agora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  venda_registro = {
      "id": len(DATABASE["vendas"]) + 1,
      "deposito_id": dep_id,
      "deposito_nome": dep["nome"],
      "quantidade": qtd,
      "pagamento": pagamento,
      "valor_total": valor_total,
      "operador": operador,
      "estoque_antes": estoque_antes,
      "estoque_depois": estoque_depois,
      "data": agora_str,
      "tem_troca": tem_troca,
  }
  DATABASE["vendas"].append(venda_registro)

  if tem_troca:
    troca_registro = {
        "id": len(DATABASE["trocas"]) + 1,
        "deposito_id": dep_id,
        "cliente": questionario.get("cliente", "Não informado"),
        "cpf": questionario.get("cpf", ""),
        "tamanho_botijao": questionario.get("tamanho", "P13"),
        "motivo": questionario.get("motivo", "Troca padrão"),
        "conferido_repesado": questionario.get("conferido", True),
        "operador": operador,
        "data": agora_str,
    }
    DATABASE["trocas"].append(troca_registro)

  return jsonify({"mensagem": "Venda registrada com sucesso!", "deposito": dep}), 200


@app.route("/api/deposito/transferir", methods=["POST"])
def transferir_estoque():
  data = request.get_json() or {}
  origem_id = int(data.get("origem_id"))
  destino_id = int(data.get("destino_id"))
  quantidade = int(data.get("quantidade", 0))
  tipo_botijao = data.get("tipo_botijao", "cheias")
  caminhao_placa = data.get("caminhao_placa")
  motorista = data.get("motorista")
  operador = data.get("operador")

  if origem_id == destino_id:
    return (
        jsonify({"erro": "Depósito de origem e destino não podem ser iguais."}),
        400,
    )

  origem = DATABASE["depositos"].get(origem_id)
  destino = DATABASE["depositos"].get(destino_id)

  if not origem or not destino:
    return jsonify({"erro": "Depósito inválido."}), 404

  if origem[tipo_botijao] < quantidade:
    return (
        jsonify({
            "erro": (
                f"Estoque insuficiente de botijões {tipo_botijao} na origem."
            )
        }),
        400,
    )

  origem[tipo_botijao] -= quantidade
  destino[tipo_botijao] += quantidade

  mov_registro = {
      "id": len(DATABASE["movimentacoes"]) + 1,
      "origem": origem["nome"],
      "destino": destino["nome"],
      "quantidade": quantidade,
      "tipo_botijao": tipo_botijao,
      "caminhao": caminhao_placa,
      "motorista": motorista,
      "operador": operador,
      "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
  }
  DATABASE["movimentacoes"].append(mov_registro)

  return jsonify({"mensagem": "Transferência realizada com sucesso!"}), 200


@app.route("/api/deposito/movimentacoes", methods=["GET"])
def listar_movimentacoes():
  return jsonify(DATABASE["movimentacoes"]), 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
