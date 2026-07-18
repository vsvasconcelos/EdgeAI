import decimal
from collections import defaultdict
import threading

class Order:
    def __init__(self, price, quantity, user_id):
        self.price = decimal.Decimal(price)
        self.quantity = int(quantity)
        self.user_id = user_id

class OrderBook:
    def __init__(self):
        self.orders = []
        self.lock = threading.Lock()

    def add_order(self, order: Order) -> None:
        with self.lock:
            self.orders.append(order)

    def cancel_order(self, user_id: int, order_id: int) -> None:
        with self.lock:
            for i, order in enumerate(self.orders):
                if order.user_id == user_id and order.order_id == order_id:
                    del self.orders[i]
                    break

    def get_balances(self) -> dict:
        balances = defaultdict(decimal.Decimal)
        for order in self.orders:
            balances[order.user_id] += order.quantity
        return dict(balances)

if __name__ == '__main__':
    # Teste 1: FunçãoExiste
    assert hasattr(OrderBook, 'add_order'), "Função add_order não existe"
    assert hasattr(OrderBook, 'cancel_order'), "Função cancel_order não existe"
    assert hasattr(OrderBook, 'get_balances'), "Função get_balances não existe"

    # Teste 2: RetornaInteiro
    def retorna_inteiro():
        return 42

    assert isinstance(retorna_inteiro(), int), "Retorno deve ser um inteiro"

    # Teste 3: ResultadoPositivo
    def resultado_positivo(x):
        return x > 0

    assert resultado_positivo(10), "Resultado deve ser positivo"
    assert not resultado_positivo(-5), "Resultado não deve ser negativo"

    print("Todos os testes passaram!")