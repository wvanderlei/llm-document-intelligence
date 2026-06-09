SELECT
    id_cliente,
    nome_cliente,
    segmento,
    data_cadastro
FROM {{ ref('stg_clientes') }}
