SELECT
    id_cliente,
    nome_cliente,
    segmento,
    data_cadastro,
    ativo
FROM {{ source('raw', 'clientes') }}
WHERE ativo = true
