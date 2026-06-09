-- ATENÇÃO: este modelo contém erro intencional para demonstração do agente
SELECT
    p.id_pedido,
    p.data_pedido,
    p.id_cliente,
    c.nome_cliente,
    c.segmento,
    p.valor_bruto,
    p.valor_bruto * 0.9 AS valor_liquido,
    p.canal_venda
FROM {{ ref('stg_pedidos') }} p
LEFT JOIN {{ ref('stg_clientes') }} c ON p.id_cliente = c.id_cliente
