1. O sistema deve atuar como um Order Book para processar ordens financeiras de compra e venda.
2. Requisitos funcionais:
   - Utilizar `decimal` para valores monetários e quantidades.
   - Implementar uma classe `OrderBook` com métodos `add_order`, `cancel_order`, e `get_balances`.
   - Processar ordens imediatamente ao serem adicionadas, priorizando Melhor Preço -> Ordem de Chegada.
   - Garantir thread-safety usando primitivos de sincronização do módulo `threading`.
3. Critérios de aceitação testáveis:
   - A soma total de dinheiro e ativos no sistema permanece constante (imutabilidade de massa financeira).
   - O sistema deve ser capaz de lidar com 10 threads simulando 1.000 usuários enviando ordens de compra e venda aleatórias simultaneamente.
4. Restrições:
   - Python puro, stdlib apenas, sem libs externas