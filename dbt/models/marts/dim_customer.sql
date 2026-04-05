with snapshot as (
    select * from {{ ref('customers_snapshot') }}
    -- remove the filter — keep ALL versions, not just current
),

final as (
    select
        {{ dbt_utils.generate_surrogate_key(['user_id', 'dbt_valid_from']) }}
                                        as customer_key,
        user_id,
        first_name,
        last_name,
        first_name || ' ' || last_name  as full_name,
        email,
        username,
        city,
        street,
        zipcode,
        phone,
        dbt_valid_from                  as effective_from,
        dbt_valid_to                    as effective_to,
        loaded_at,
        load_date
    from snapshot
)

select * from final