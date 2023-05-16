from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)
df = pd.read_csv('transactions.csv', sep=";")

@app.route('/anti_fraud', methods=['POST'])
def anti_fraud():
    # Ler arquivo CSV
    df = pd.read_csv('transactions.csv', sep=";")
    df['transaction_date'] = pd.to_datetime(df['transaction_date'])

    # Receber os dados da transação enviados no corpo da requisição
    dados_transacao = request.json
    transaction_id = dados_transacao['transaction_id']
    merchant_id = dados_transacao['merchant_id']
    user_id = dados_transacao['user_id']
    card_number = dados_transacao['card_number']
    transaction_date = dados_transacao['transaction_date']
    transaction_amount = dados_transacao['transaction_amount']
    device_id = dados_transacao['device_id']

    # Regras de validação
    motivos_rejeicao = []
    # Regra 1: Rejeitar transação se o usuário estiver tentando muitas transações seguidas
    num_transacoes = df.loc[df['user_id'] == user_id].shape[0]
    if num_transacoes >= 10:
        motivos_rejeicao.append("Usuário realizou muitas transações seguidas.")

    # Regra 2: Rejeitar transações acima de um certo valor em um determinado período
    data_atual = pd.Timestamp.now()
    data_inicio_periodo = data_atual - pd.Timedelta(days=7)
    valor_total_periodo = df.loc[(df['user_id'] == user_id) & (df['transaction_date'] >= data_inicio_periodo) & (df['transaction_amount'] > 1000), 'transaction_amount'].sum()
    if valor_total_periodo + transaction_amount > 10000:
        motivos_rejeicao.append("Valor total das transações do usuário em um período de 7 dias ultrapassou o limite permitido.")

    # Regra 3: Rejeitar transação se o usuário teve um chargeback antes
    teve_chargeback = df.loc[(df['user_id'] == user_id) & (df['has_cbk'] == True)].shape[0]
    if teve_chargeback > 0:
        motivos_rejeicao.append("Usuário teve um chargeback em transação anterior.")

    # Regra 4: Rejeitar se o mesmo cartão foi utilizado em transações que somam mais de R$ 1000 em um período de 1 hora
    data_atual = pd.Timestamp.now()
    data_inicio_periodo = data_atual - pd.Timedelta(hours=1)
    valor_total_periodo = df.loc[(df['user_id'] == user_id) & (df['card_number'] == card_number) & (df['transaction_date'] >= data_inicio_periodo), 'transaction_amount'].sum()
    if valor_total_periodo > 1000:
        motivos_rejeicao.append("O mesmo cartão foi utilizado em transações que somam mais de R$ 1000 em um período de 1 hora.")

    # Regra 5: Rejeitar se houver mais de 3 transaction_id do mesmo card_number em um intervalo de 1 hora
    data_atual = pd.Timestamp.now()
    data_inicio_periodo = data_atual - pd.Timedelta(hours=1)
    num_transaction_id = df.loc[(df['card_number'] == card_number) & (df['transaction_date']>= data_inicio_periodo) & (df['transaction_id'] != transaction_id), 'transaction_id'].nunique()
    if num_transaction_id > 3:
        motivos_rejeicao.append("Há mais de 3 transaction_id do mesmo card_number em um intervalo de 1 hora.")

    # Verificar se a transação foi aprovada ou rejeitada e os motivos de rejeição
    if motivos_rejeicao:
        return jsonify({'transaction_id': transaction_id, 'recommendation': 'deny', 'reasons': motivos_rejeicao})
    else:
        return jsonify({'transaction_id': transaction_id, 'recommendation': 'approve'})


if __name__ == '__main__':
    app.run()

