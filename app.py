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

            # Пагинация для получения заказов до 500 штук
            while len(orders) < max_orders:
                current_orders = None
                start_time = time.time()  # Начало попыток для данного запроса
                last_error = None

                # Вложенный цикл с повторными попытками; если 30 секунд подряд не удаётся получить ответ без ошибок,
                # возвращается последняя ошибка
                while current_orders is None:
                    try:
                        current_orders = w.get_own_p2p_order_history(offset, limit, "COMPLETED_FOR_REQUESTER")
                    except Exception as e:
                        last_error = e
                        logger.error(f"Ошибка при получении заказов с offset={offset}: {e}. Повтор через 1 секунду.")
                        if time.time() - start_time > 30:
                            logger.error("За последние 30 секунд не удалось получить успешный ответ. Возврат последней ошибки.")
                            return jsonify({"error": str(last_error)}), 500
                        time.sleep(1)

                # Если данных больше нет, завершаем пагинацию
                if not current_orders:
                    logger.info("Новых заказов не найдено, завершаем цикл.")
                    break

                orders.extend(current_orders)
                logger.info(f"Общее количество полученных заказов: {len(orders)}")

                # Если получено меньше, чем limit, то достигнут конец данных
                if len(current_orders) < limit:
                    break

                offset += limit

            # Если заказов больше max_orders, оставляем только последние 500
            if len(orders) > max_orders:
                orders = orders[:max_orders]

            # Преобразование заказов в формат JSON
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
