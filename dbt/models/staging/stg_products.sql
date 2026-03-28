with source as (
    select * from {{ source('raw', 'products') }}
),

deduplicated as (
    select *,
        row_number() over (
            partition by id, _run_id
            order by _loaded_at desc
        ) as row_num
    from source
),

final as (
    select
        id                              as product_id,
        title                           as product_name,
        price                           as price,
        description                     as description,
        category                        as category,
        image                           as image_url,
        rating:rate::float              as rating_score,
        rating:count::integer           as rating_count,
        _loaded_at                      as loaded_at,
        _source                         as source_system,
        _load_date                      as load_date,
        _run_id                         as run_id
    from deduplicated
    where row_num = 1
)

select * from final