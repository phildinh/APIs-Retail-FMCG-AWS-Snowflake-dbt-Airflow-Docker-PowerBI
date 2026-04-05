with snapshot as (
    select * from {{ ref('products_snapshot') }}
    -- remove the filter — keep ALL versions, not just current
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['product_id', 'dbt_valid_from']) }}
                                        as product_key,
        product_id,
        product_name,
        category,
        price,
        description,
        image_url,
        rating_score,
        rating_count,
        dbt_valid_from                  as effective_from,
        dbt_valid_to                    as effective_to,
        loaded_at,
        load_date
    from snapshot
)

select * from final