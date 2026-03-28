with carts as (
    select * from {{ ref('stg_carts') }}
),

seed_data as (
    select * from {{ ref('fact_order_items_seed') }}
),

products as (
    select * from {{ ref('dim_product') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
),

dates as (
    select * from {{ ref('dim_date') }}
),

pipeline_orders as (
    select
        {{ dbt_utils.generate_surrogate_key(['c.cart_id', 'c.product_id']) }}
                                            as order_item_key,
        c.cart_id                           as order_id,
        cust.customer_key,
        p.product_key,
        d.date_key,
        c.product_id,
        c.user_id,
        c.quantity,
        p.price                             as unit_price,
        c.quantity * p.price                as total_price,
        c.cart_date                         as order_date,
        c.loaded_at,
        null::varchar                       as run_id
    from carts c
    left join products p
        on c.product_id = p.product_id
    left join customers cust
        on c.user_id = cust.user_id
    left join dates d
        on to_number(to_char(c.cart_date::date, 'YYYYMMDD')) = d.date_key
),

seed_orders as (
    select
        {{ dbt_utils.generate_surrogate_key(['s.order_item_id']) }}
                                            as order_item_key,
        s.order_id,
        cust.customer_key,
        p.product_key,
        d.date_key,
        s.product_id,
        s.user_id,
        s.quantity,
        s.unit_price,
        s.total_price,
        s.order_date,
        null::timestamp_tz                  as loaded_at,
        null::varchar                       as run_id
    from seed_data s
    left join products p
        on s.product_id = p.product_id
    left join customers cust
        on s.user_id = cust.user_id
    left join dates d
        on to_number(to_char(s.order_date::date, 'YYYYMMDD')) = d.date_key
),

final as (
    select * from pipeline_orders
    union all
    select * from seed_orders
)

select * from final