from flask import Flask, request, jsonify
from wallet.rest import Wallet
import os

app = Flask(__name__)

@app.route('/get_orders', methods=['POST'])
def get_orders():
    token = request.form.get('token')

    if not token:
        return jsonify({"error": "Token is missing"}), 400

    token = token.replace('\n', '')

    with open('token.txt', 'w') as f:
        f.write(token)

    w = Wallet.token_from_file('token.txt')
    orders = w.get_own_p2p_order_history(0, 100, "COMPLETED_FOR_REQUESTER")

    orders_json = []
    for order in orders:
        order_info = {
            "order_id": order.id,
            "amount": {
                "value": order.amount.amount,
                "currency_code": order.amount.currencyCode
            },
            "buyer_id": order.buyer.userId,
            "seller_id": order.seller.userId,
            "payment_method": order.paymentDetails.paymentMethod.name if order.paymentDetails and order.paymentDetails.paymentMethod else None,
            "status": order.status,
            "status_update_time": order.statusUpdateDateTime
        }
        orders_json.append(order_info)

    return jsonify(orders_json)

if __name__ == '__main__':
    if os.path.exists('token.txt'):
        os.remove('token.txt')

    host_ip = '0.0.0.0'
    port = 9000
    server_address = f"http://{host_ip}:{port}"

    print(f"Server is running on {server_address}")

    app.run(host=host_ip, port=port, debug=True)
