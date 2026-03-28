with carts as (
    select * from {{ ref('stg_carts') }}
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

joined as (
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
        c.run_id
    from carts c
    left join products p
        on c.product_id = p.product_id
    left join customers cust
        on c.user_id = cust.user_id
    left join dates d
        on to_number(to_char(c.cart_date::date, 'YYYYMMDD')) = d.date_key
),

final as (
    select * from joined
)

select * from final