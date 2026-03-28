with source as (
    select * from {{ source('raw', 'users') }}
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
        id                              as user_id,
        email                           as email,
        username                        as username,
        name:firstname::varchar         as first_name,
        name:lastname::varchar          as last_name,
        address:city::varchar           as city,
        address:street::varchar         as street,
        address:zipcode::varchar        as zipcode,
        address:geolocation:lat::float  as latitude,
        address:geolocation:long::float as longitude,
        phone                           as phone,
        _loaded_at                      as loaded_at,
        _source                         as source_system,
        _load_date                      as load_date,
        _run_id                         as run_id
    from deduplicated
    where row_num = 1
)

select * from final