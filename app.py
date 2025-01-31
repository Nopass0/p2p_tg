from flask import Flask, request, jsonify
from wallet.rest import Wallet
import os
import time
import logging
import sys
from werkzeug.serving import run_simple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    @app.route('/get_orders', methods=['POST'])
    def get_orders():
        try:
            token = request.form.get('token')

            if not token:
                return jsonify({"error": "Token is missing"}), 400

            token = token.replace('\n', '')

            logger.info("Received token request")

            with open('token.txt', 'w') as f:
                f.write(token)

            w = Wallet.token_from_file('token.txt')
            orders = w.get_own_p2p_order_history(0, 100, "COMPLETED_FOR_REQUESTER")

            logger.info(f"Retrieved {len(orders) if orders else 0} orders")

            orders_json = []
            for order in orders:
                order_info = {
                    "order_id": order.id,
                    "amount": {
                        "value": order.amount.amount if order.amount else None,
                        "currency_code": order.amount.currencyCode if order.amount else None
                    },
                    "volume": {
                        "value": order.volume.amount if order.volume else None,
                        "currency_code": order.volume.currencyCode if order.volume else None
                    },
                    "buyer_id": order.buyer.userId if order.buyer else None,
                    "seller_id": order.seller.userId if order.seller else None,
                    "payment_method": order.paymentDetails.paymentMethod.name if order.paymentDetails and order.paymentDetails.paymentMethod else None,
                    "status": order.status,
                    "status_update_time": order.statusUpdateDateTime
                }
                orders_json.append(order_info)

            return jsonify(orders_json)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return app

def run_server(host_ip='0.0.0.0', port=9000):
    while True:
        try:
            if os.path.exists('token.txt'):
                os.remove('token.txt')

            server_address = f"http://{host_ip}:{port}"
            logger.info(f"Starting server on {server_address}")

            app = create_app()
            run_simple(host_ip, port, app, use_reloader=False)
        except Exception as e:
            logger.error(f"Server crashed with error: {str(e)}")
            logger.info("Restarting server in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    run_server()
