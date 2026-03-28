with source as (
    select * from {{ source('raw', 'carts') }}
),

deduplicated as (
    select *,
        row_number() over (
            partition by id, _run_id
            order by _loaded_at desc
        ) as row_num
    from source
),

flattened as (
    select
        c.id                                as cart_id,
        c.userid                            as user_id,
        c.date                              as cart_date,
        p.value:productId::integer          as product_id,
        p.value:quantity::integer           as quantity,
        c._loaded_at                        as loaded_at,
        c._source                           as source_system,
        c._load_date                        as load_date,
        c._run_id                           as run_id
    from deduplicated c,
    lateral flatten(input => c.products)    as p
    where c.row_num = 1
),

final as (
    select * from flattened
)

select * from final