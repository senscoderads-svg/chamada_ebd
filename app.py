import datetime
import os

from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuração da conexão com o banco de dados
def obter_conexao():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "PRESENCA_ALUNOS")
    )

# ROTA GET: Busca o novo relatório resumido (Sua nova Query)
@app.route('/buscar_presencas', methods=['GET'])
def buscar_presencas():
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor(dictionary=True)
        
        query = """
            SELECT A.ID_ATIVIDADE AS id_atividade,
                   DATE_FORMAT(A.DATA_ATIVIDADE, '%d/%m/%Y') AS data,
                   A.TIPO_ATIVIDADE AS atividade,
                   A.STATUS_ATIVIDADE AS status,
                   DATE_FORMAT(A.DATA_INICIO, '%d/%m/%Y %H:%i') AS data_inicio,
                   DATE_FORMAT(A.DATA_FIM, '%d/%m/%Y %H:%i') AS data_fim,
                   COALESCE((SELECT GROUP_CONCAT(DISTINCT PR.NOME_PROFESSOR SEPARATOR ', ')
                             FROM PROFESSOR_ATIVIDADE_LECIONA PAL
                             JOIN PROFESSOR PR ON PR.ID_PROFESSOR = PAL.FK_PROFESSOR_ID_PROFESSOR
                             WHERE PAL.FK_ATIVIDADE_ID_ATIVIDADE = A.ID_ATIVIDADE), 'Não alocado') AS professor,
                   COALESCE((SELECT GROUP_CONCAT(DISTINCT P.NOME_PESSOA SEPARATOR ', ')
                             FROM ALUNOS_PRESENTES_PARTICIPA APP
                             JOIN PESSOA_CADASTRAR P ON P.ID_PESSOA = APP.FK_PESSOA_CADASTRAR_ID_PESSOA
                                AND P.ID_CADASTRO = APP.FK_PESSOA_CADASTRAR_ID_CADASTRO
                             WHERE APP.FK_ATIVIDADE_ID_ATIVIDADE = A.ID_ATIVIDADE
                               AND APP.STATUS_PRESENCA = 'Presente'), 'Nenhum aluno presente') AS presentes_nomes,
                   (SELECT COUNT(*) FROM ALUNOS_PRESENTES_PARTICIPA APP
                    WHERE APP.FK_ATIVIDADE_ID_ATIVIDADE = A.ID_ATIVIDADE AND APP.STATUS_PRESENCA = 'Presente') AS presentes,
                   (SELECT COUNT(*) FROM ALUNOS_PRESENTES_PARTICIPA APP
                    WHERE APP.FK_ATIVIDADE_ID_ATIVIDADE = A.ID_ATIVIDADE AND APP.STATUS_PRESENCA = 'Ausente') AS ausentes
            FROM ATIVIDADE A
            ORDER BY A.DATA_ATIVIDADE DESC;
        """
        cursor.execute(query)
        resultados = cursor.fetchall()
        return jsonify(resultados), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@app.route('/listar_alunos', methods=['GET'])
def listar_alunos():
    return listar_registros("""
        SELECT ID_PESSOA AS id_pessoa, ID_CADASTRO AS id_cadastro,
               NOME_PESSOA AS nome_pessoa, DATE_FORMAT(DATA_NASCIMENTO, '%Y-%m-%d') AS data_nascimento,
               TIMESTAMPDIFF(YEAR, DATA_NASCIMENTO, CURDATE()) AS idade,
               DATA_CADASTRO AS data_cadastro
        FROM PESSOA_CADASTRAR WHERE TIPO = 'Aluno' ORDER BY NOME_PESSOA
    """)

@app.route('/detalhes_aluno', methods=['GET'])
def detalhes_aluno():
    id_pessoa = request.args.get('id_pessoa')
    id_cadastro = request.args.get('id_cadastro')
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("""
            SELECT ID_PESSOA AS id_pessoa, ID_CADASTRO AS id_cadastro,
                   NOME_PESSOA AS nome_pessoa, DATA_NASCIMENTO AS data_nascimento,
                   TIMESTAMPDIFF(YEAR, DATA_NASCIMENTO, CURDATE()) AS idade,
                   DATA_CADASTRO AS data_cadastro, OBSERVACAO AS observacao
            FROM PESSOA_CADASTRAR
            WHERE ID_PESSOA = %s AND ID_CADASTRO = %s AND TIPO = 'Aluno'
        """, (id_pessoa, id_cadastro))
        aluno = cursor.fetchone()
        if not aluno:
            return jsonify({"erro": "Aluno não encontrado."}), 404
        cursor.execute("""
            SELECT A.ID_ATIVIDADE AS id_atividade, A.TIPO_ATIVIDADE AS atividade,
                   DATE_FORMAT(A.DATA_ATIVIDADE, '%d/%m/%Y') AS data,
                   A.STATUS_ATIVIDADE AS status, APP.STATUS_PRESENCA AS presenca,
                   DATE_FORMAT(A.DATA_INICIO, '%d/%m/%Y %H:%i') AS data_inicio,
                   DATE_FORMAT(A.DATA_FIM, '%d/%m/%Y %H:%i') AS data_fim
            FROM ALUNOS_PRESENTES_PARTICIPA APP
            JOIN ATIVIDADE A ON A.ID_ATIVIDADE = APP.FK_ATIVIDADE_ID_ATIVIDADE
            WHERE APP.FK_PESSOA_CADASTRAR_ID_PESSOA = %s
              AND APP.FK_PESSOA_CADASTRAR_ID_CADASTRO = %s
            ORDER BY A.DATA_ATIVIDADE DESC
        """, (id_pessoa, id_cadastro))
        aluno['historico'] = cursor.fetchall()
        return jsonify(aluno), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@app.route('/ranking_alunos', methods=['GET'])
def ranking_alunos():
    return listar_registros("""
        SELECT P.ID_PESSOA AS id_pessoa, P.ID_CADASTRO AS id_cadastro,
               P.NOME_PESSOA AS nome_pessoa,
               COUNT(DISTINCT CASE WHEN APP.STATUS_PRESENCA = 'Presente' THEN A.ID_ATIVIDADE END) AS participacoes,
               COUNT(DISTINCT A.ID_ATIVIDADE) AS atividades_encerradas,
               ROUND(100 * COUNT(DISTINCT CASE WHEN APP.STATUS_PRESENCA = 'Presente' THEN A.ID_ATIVIDADE END) / NULLIF(COUNT(DISTINCT A.ID_ATIVIDADE), 0), 0) AS percentual
        FROM PESSOA_CADASTRAR P
        JOIN ALUNOS_PRESENTES_PARTICIPA APP
          ON APP.FK_PESSOA_CADASTRAR_ID_PESSOA = P.ID_PESSOA
         AND APP.FK_PESSOA_CADASTRAR_ID_CADASTRO = P.ID_CADASTRO
        JOIN ATIVIDADE A ON A.ID_ATIVIDADE = APP.FK_ATIVIDADE_ID_ATIVIDADE
        WHERE P.TIPO = 'Aluno' AND A.STATUS_ATIVIDADE = 'Encerrada'
        GROUP BY P.ID_PESSOA, P.ID_CADASTRO, P.NOME_PESSOA
        ORDER BY participacoes DESC, percentual DESC, P.NOME_PESSOA
    """)

@app.route('/listar_professores', methods=['GET'])
def listar_professores():
    return listar_registros("""
        SELECT ID_PROFESSOR AS id_professor, NOME_PROFESSOR AS nome_professor,
               DATA_NASCIMENTO AS data_nascimento,
               TIMESTAMPDIFF(YEAR, DATA_NASCIMENTO, CURDATE()) AS idade,
               FK_DEPARTAMENTO_ID AS id_departamento
        FROM PROFESSOR ORDER BY NOME_PROFESSOR
    """)

@app.route('/listar_atividades', methods=['GET'])
def listar_atividades():
    return listar_registros("""
        SELECT ID_ATIVIDADE AS id_atividade,
               DATE_FORMAT(DATA_ATIVIDADE, '%d/%m/%Y') AS data,
               DATE_FORMAT(DATA_ATIVIDADE, '%Y-%m-%d') AS data_iso,
               TIPO_ATIVIDADE AS atividade,
               STATUS_ATIVIDADE AS status,
               DATE_FORMAT(DATA_INICIO, '%d/%m/%Y %H:%i') AS data_inicio,
               DATE_FORMAT(DATA_FIM, '%d/%m/%Y %H:%i') AS data_fim,
               (SELECT FK_PROFESSOR_ID_PROFESSOR FROM PROFESSOR_ATIVIDADE_LECIONA
            WHERE FK_ATIVIDADE_ID_ATIVIDADE = ATIVIDADE.ID_ATIVIDADE LIMIT 1) AS id_professor
        FROM ATIVIDADE ORDER BY DATA_ATIVIDADE DESC
    """)

@app.route('/editar_aluno', methods=['PUT'])
def editar_aluno():
    dados = request.get_json(silent=True) or {}
    return atualizar_nome("UPDATE PESSOA_CADASTRAR SET NOME_PESSOA = %s, DATA_NASCIMENTO = %s WHERE ID_PESSOA = %s AND ID_CADASTRO = %s", (dados.get('nome'), dados.get('data_nascimento') or None, dados.get('id_pessoa'), dados.get('id_cadastro')), 'Aluno atualizado com sucesso!')

@app.route('/editar_professor', methods=['PUT'])
def editar_professor():
    dados = request.get_json(silent=True) or {}
    return atualizar_nome("UPDATE PROFESSOR SET NOME_PROFESSOR = %s WHERE ID_PROFESSOR = %s", (dados.get('nome'), dados.get('id_professor')), 'Professor atualizado com sucesso!')

@app.route('/editar_atividade', methods=['PUT'])
def editar_atividade():
    dados = request.get_json(silent=True) or {}
    conexao = None
    cursor = None
    try:
        status = dados.get('status') or 'Agendada'
        if not dados.get('nome', '').strip() or not dados.get('data_atividade'):
            return jsonify({"erro": "Nome e data da atividade são obrigatórios."}), 400
        if status not in ('Agendada', 'Em andamento', 'Encerrada'):
            return jsonify({"erro": "Status de atividade inválido."}), 400
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute("SELECT DATA_INICIO, DATA_FIM, STATUS_ATIVIDADE FROM ATIVIDADE WHERE ID_ATIVIDADE = %s", (dados['id_atividade'],))
        atividade_atual = cursor.fetchone()
        if not atividade_atual:
            return jsonify({"erro": "Atividade não encontrada."}), 404
        data_inicio, data_fim = atividade_atual[0], atividade_atual[1]
        if status == 'Agendada':
            data_inicio = None
            data_fim = None
        elif status == 'Em andamento':
            data_inicio = data_inicio or datetime.datetime.now()
            data_fim = None
        elif status == 'Encerrada':
            data_inicio = data_inicio or datetime.datetime.now()
            data_fim = data_fim or datetime.datetime.now()
        cursor.execute("""UPDATE ATIVIDADE
            SET TIPO_ATIVIDADE = %s, DATA_ATIVIDADE = %s, STATUS_ATIVIDADE = %s,
                DATA_INICIO = %s, DATA_FIM = %s
            WHERE ID_ATIVIDADE = %s""", (dados['nome'].strip(), dados['data_atividade'], status, data_inicio, data_fim, dados['id_atividade']))
        cursor.execute("DELETE FROM PROFESSOR_ATIVIDADE_LECIONA WHERE FK_ATIVIDADE_ID_ATIVIDADE = %s", (dados['id_atividade'],))
        if dados.get('id_professor'):
            cursor.execute("SELECT COALESCE(MAX(ID_PROFESSOR_ATIVIDADE), 0) + 1 FROM PROFESSOR_ATIVIDADE_LECIONA")
            cursor.execute("INSERT INTO PROFESSOR_ATIVIDADE_LECIONA (ID_PROFESSOR_ATIVIDADE, FK_ATIVIDADE_ID_ATIVIDADE, FK_PROFESSOR_ID_PROFESSOR) VALUES (%s, %s, %s)", (cursor.fetchone()[0], dados['id_atividade'], dados['id_professor']))
        conexao.commit()
        return jsonify({"mensagem": "Atividade atualizada com sucesso!"}), 200
    except Exception as e:
        if conexao:
            conexao.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

def atualizar_nome(query, valores, mensagem):
    conexao = None
    cursor = None
    try:
        if not valores[0] or not str(valores[0]).strip():
            return jsonify({"erro": "O nome não pode ficar vazio."}), 400
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(query, valores)
        conexao.commit()
        return jsonify({"mensagem": mensagem}), 200
    except Exception as e:
        if conexao:
            conexao.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

def listar_registros(query):
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(query)
        return jsonify(cursor.fetchall()), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

def excluir_registros(query, valores):
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(query, valores)
        conexao.commit()
        return jsonify({"mensagem": "Registro excluído com sucesso!"}), 200
    except Exception as e:
        if conexao:
            conexao.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

def excluir_em_ordem(comandos):
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        for query, valores in comandos:
            cursor.execute(query, valores)
        conexao.commit()
        return jsonify({"mensagem": "Registro excluído com sucesso!"}), 200
    except Exception as e:
        if conexao:
            conexao.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@app.route('/excluir_aluno', methods=['DELETE'])
def excluir_aluno():
    dados = request.get_json(silent=True) or {}
    valores = (dados.get('id_pessoa'), dados.get('id_cadastro'))
    return excluir_em_ordem([
        ("""DELETE FROM ALUNOS_PRESENTES_PARTICIPA
           WHERE FK_PESSOA_CADASTRAR_ID_PESSOA = %s
             AND FK_PESSOA_CADASTRAR_ID_CADASTRO = %s""", valores),
        ("""DELETE FROM PESSOA_CADASTRAR
           WHERE ID_PESSOA = %s AND ID_CADASTRO = %s""", valores)
    ])

@app.route('/excluir_professor', methods=['DELETE'])
def excluir_professor():
    dados = request.get_json(silent=True) or {}
    valor = (dados.get('id_professor'),)
    return excluir_em_ordem([
        ("DELETE FROM PROFESSOR_ATIVIDADE_LECIONA WHERE FK_PROFESSOR_ID_PROFESSOR = %s", valor),
        ("DELETE FROM PROFESSOR WHERE ID_PROFESSOR = %s", valor)
    ])

@app.route('/excluir_atividade', methods=['DELETE'])
def excluir_atividade():
    dados = request.get_json(silent=True) or {}
    valor = (dados.get('id_atividade'),)
    return excluir_em_ordem([
        ("DELETE FROM ALUNOS_PRESENTES_PARTICIPA WHERE FK_ATIVIDADE_ID_ATIVIDADE = %s", valor),
        ("DELETE FROM PROFESSOR_ATIVIDADE_LECIONA WHERE FK_ATIVIDADE_ID_ATIVIDADE = %s", valor),
        ("DELETE FROM ATIVIDADE WHERE ID_ATIVIDADE = %s", valor)
    ])

@app.route('/iniciar_atividade', methods=['POST'])
def iniciar_atividade():
    return alterar_status_atividade(
        """UPDATE ATIVIDADE SET STATUS_ATIVIDADE = 'Em andamento', DATA_INICIO = NOW()
           WHERE ID_ATIVIDADE = %s AND STATUS_ATIVIDADE = 'Agendada'""",
        'Atividade iniciada com sucesso!'
    )

@app.route('/encerrar_atividade', methods=['POST'])
def encerrar_atividade():
    return alterar_status_atividade(
        """UPDATE ATIVIDADE SET STATUS_ATIVIDADE = 'Encerrada', DATA_FIM = NOW()
           WHERE ID_ATIVIDADE = %s AND STATUS_ATIVIDADE = 'Em andamento'""",
        'Atividade encerrada com sucesso!'
    )

def alterar_status_atividade(query, mensagem):
    dados = request.get_json(silent=True) or {}
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute(query, (dados.get('id_atividade'),))
        if cursor.rowcount == 0:
            return jsonify({"erro": "A atividade não está no status correto para esta ação."}), 409
        conexao.commit()
        return jsonify({"mensagem": mensagem}), 200
    except Exception as e:
        if conexao:
            conexao.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ROTA POST: Cadastrar Departamento
@app.route('/inserir_departamento', methods=['POST'])
def inserir_departamento():
    dados = request.json
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        query = "INSERT INTO DEPARTAMENTO (ID_DEPARTAMENTO, NOME_DEPARTAMENTO) VALUES (%s, %s)"
        cursor.execute(query, (dados['id_departamento'], dados['nome_departamento']))
        conexao.commit()
        return jsonify({"mensagem": "Departamento cadastrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ROTA POST: Cadastrar Aluno
@app.route('/inserir_aluno', methods=['POST'])
def inserir_aluno():
    dados = request.json
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        valores = (dados['id_pessoa'], dados['id_cadastro'], dados['nome_pessoa'], dados.get('data_nascimento') or None, 'Aluno', dados['data_cadastro'], dados['observacao'])
        query = """
            INSERT INTO PESSOA_CADASTRAR
                (ID_PESSOA, ID_CADASTRO, NOME_PESSOA, DATA_NASCIMENTO, TIPO, DATA_CADASTRO, OBSERVACAO)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, valores)
        conexao.commit()
        return jsonify({"mensagem": "Aluno cadastrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ROTA POST: Cadastrar Professor (Com FK de Departamento)
@app.route('/inserir_professor', methods=['POST'])
def inserir_professor():
    dados = request.json
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        query = """INSERT INTO PROFESSOR
            (ID_PROFESSOR, NOME_PROFESSOR, DATA_NASCIMENTO)
            VALUES (%s, %s, %s)"""
        cursor.execute(query, (dados['id_professor'], dados['nome_professor'], dados.get('data_nascimento') or None))
        conexao.commit()
        return jsonify({"mensagem": "Professor cadastrado com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ROTA POST: Cadastrar Atividade
@app.route('/inserir_atividade', methods=['POST'])
def inserir_atividade():
    dados = request.json
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        query = "INSERT INTO ATIVIDADE (ID_ATIVIDADE, DATA_ATIVIDADE, TIPO_ATIVIDADE) VALUES (%s, %s, %s)"
        cursor.execute(query, (dados['id_atividade'], dados['data_atividade'], dados['tipo_atividade']))

        id_professor = dados.get('id_professor')
        if id_professor is not None:
            cursor.execute("SELECT COALESCE(MAX(ID_PROFESSOR_ATIVIDADE), 0) + 1 FROM PROFESSOR_ATIVIDADE_LECIONA")
            id_professor_atividade = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO PROFESSOR_ATIVIDADE_LECIONA
                    (ID_PROFESSOR_ATIVIDADE, FK_ATIVIDADE_ID_ATIVIDADE, FK_PROFESSOR_ID_PROFESSOR)
                VALUES (%s, %s, %s)
            """, (id_professor_atividade, dados['id_atividade'], id_professor))

        conexao.commit()
        return jsonify({"mensagem": "Atividade cadastrada com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

@app.route('/vincular_professor', methods=['POST'])
def vincular_professor():
    dados = request.json or {}
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute("SELECT COALESCE(MAX(ID_PROFESSOR_ATIVIDADE), 0) + 1 FROM PROFESSOR_ATIVIDADE_LECIONA")
        id_professor_atividade = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO PROFESSOR_ATIVIDADE_LECIONA
                (ID_PROFESSOR_ATIVIDADE, FK_ATIVIDADE_ID_ATIVIDADE, FK_PROFESSOR_ID_PROFESSOR)
            VALUES (%s, %s, %s)
        """, (id_professor_atividade, dados['id_atividade'], dados['id_professor']))
        conexao.commit()
        return jsonify({"mensagem": "Professor vinculado à atividade!"}), 201
    except Exception as e:
        if conexao:
            conexao.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ROTA POST: Lançar Chamada / Presença
@app.route('/inserir_presenca', methods=['POST'])
def registrar_presenca():
    dados = request.json
    conexao = None
    cursor = None
    try:
        conexao = obter_conexao()
        cursor = conexao.cursor()
        id_presenca = dados.get('id_alunos_presentes')
        if id_presenca is None:
            cursor.execute("SELECT COALESCE(MAX(ID_ALUNOS_PRESENTES), 0) + 1 FROM ALUNOS_PRESENTES_PARTICIPA")
            id_presenca = cursor.fetchone()[0]
        query = """
            INSERT INTO ALUNOS_PRESENTES_PARTICIPA 
            (ID_ALUNOS_PRESENTES, STATUS_PRESENCA, FK_PESSOA_CADASTRAR_ID_PESSOA, FK_PESSOA_CADASTRAR_ID_CADASTRO, FK_ATIVIDADE_ID_ATIVIDADE) 
            VALUES (%s, %s, %s, %s, %s)
        """
        valores = (
            id_presenca, dados['status_presenca'],
            dados['fk_pessoa_id_pessoa'], dados['fk_pessoa_id_cadastro'],
            dados['fk_atividade_id_atividade']
        )
        cursor.execute(query, valores)
        conexao.commit()
        return jsonify({"mensagem": "Presença registrada com sucesso!"}), 201
    except Exception as e:
        return jsonify({"erro": str(e)}), 400
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
