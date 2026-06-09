SELECT
    id_pedido,
    id_cliente,
    data_pedido,
    valor_total,
    status,
    canal_venda
FROM {{ source('raw', 'pedidos') }}
WHERE status != 'cancelado'
