1. `add_order(self, order: Order) -> None`
   - `order`: Instância de `Order` com campos `price`, `quantity`, e `user_id`.

2. `cancel_order(self, user_id: int, order_id: int) -> None`
   - `user_id`: ID do usuário que fez a ordem.
   - `order_id`: ID da ordem a ser cancelada.

3. `get_balances(self) -> dict`
   - Retorna um dicionário com as quantidades de dinheiro e ativos por usuário.

4. Algoritmo: Implementar uma fila de prioridade para processamento das ordens, garantindo thread-safety usando locks ou semaforos.

5. Fluxo:
   - `add_order`: Adiciona a ordem à fila de prioridade.
   - `cancel_order`: Remove a ordem da fila se o usuário for o dono dela.
   - `get_balances`: Retorna um dicionário com as quantidades atualizadas.