with date_spine as (
    select
        dateadd(day, seq4(), '2024-01-01'::date) as full_date
    from table(generator(rowcount => 730))
),

final as (
    select
        to_number(to_char(full_date, 'YYYYMMDD'))   as date_key,
        full_date                                    as full_date,
        dayofweek(full_date)                         as day_of_week,
        dayname(full_date)                           as day_name,
        month(full_date)                             as month,
        monthname(full_date)                         as month_name,
        quarter(full_date)                           as quarter,
        year(full_date)                              as year,
        case
            when dayofweek(full_date) in (0, 6)
            then true else false
        end                                          as is_weekend
    from date_spine
)

select * from final