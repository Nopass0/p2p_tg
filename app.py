from flask import Flask, request, jsonify
from wallet.rest import Wallet
import os
import time
import logging
from werkzeug.serving import run_simple

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_page_with_timeout(wallet, offset, limit, status, timeout=30):
    """
    Пытается получить страницу истории заказов с указанным offset и limit.
    Если в течение timeout секунд не удаётся получить успешный ответ,
    выбрасывает последнее возникшее исключение.
    """
    start_time = time.time()
    last_error = None
    attempt = 1
    while True:
        try:
            result = wallet.get_own_p2p_order_history(offset, limit, status)
            return result
        except Exception as e:
            last_error = e
            logger.error(f"Ошибка при получении заказов с offset={offset}: {e}. Попытка #{attempt}")
            attempt += 1
            if time.time() - start_time > timeout:
                logger.error("За последние 30 секунд не удалось получить успешный ответ. Возврат последней ошибки.")
                raise last_error
            time.sleep(1)

def create_app():
    app = Flask(__name__)

    @app.route('/get_orders', methods=['POST'])
    def get_orders():
        try:
            token = request.form.get('token')
            if not token:
                return jsonify({"error": "Token is missing"}), 400

            token = token.replace('\n', '')
            logger.info("Получен запрос с токеном")

            # Сохраняем токен во временный файл
            with open('token.txt', 'w') as f:
                f.write(token)

            w = Wallet.token_from_file('token.txt')

            offset = 0
            limit = 100
            max_orders = 500
            orders = []

            # Пагинация для получения заказов до max_orders
            while len(orders) < max_orders:
                try:
                    current_orders = get_page_with_timeout(w, offset, limit, "COMPLETED_FOR_REQUESTER", timeout=30)
                except Exception as error:
                    # Если для текущей страницы не удалось получить ответ без ошибок в течение 30 секунд,
                    # возвращаем последнюю ошибку клиенту
                    return jsonify({"error": str(error)}), 500

                if not current_orders:
                    logger.info("Новых заказов не найдено, завершаем пагинацию.")
                    break

                orders.extend(current_orders)
                logger.info(f"Общее количество полученных заказов: {len(orders)}")

                # Если в последнем запросе заказов меньше лимита, значит данные закончились
                if len(current_orders) < limit:
                    break

                offset += limit

            # Если заказов больше max_orders, оставляем только первые 500 (предполагается, что они отсортированы от новых к старым)
            if len(orders) > max_orders:
                orders = orders[:max_orders]

            # Преобразование заказов в JSON-совместимый формат
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
            logger.error(f"Ошибка обработки запроса: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return app

def run_server(host_ip='0.0.0.0', port=9000):
    while True:
        try:
            if os.path.exists('token.txt'):
                os.remove('token.txt')

            server_address = f"http://{host_ip}:{port}"
            logger.info(f"Запуск сервера на {server_address}")

            app = create_app()
            run_simple(host_ip, port, app, use_reloader=False)
        except Exception as e:
            logger.error(f"Сервер завершился с ошибкой: {str(e)}")
            logger.info("Перезапуск сервера через 5 секунд...")
            time.sleep(5)

if __name__ == '__main__':
    run_server()
