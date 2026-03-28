{% snapshot customers_snapshot %}

{{
    config(
        target_schema='MARTS',
        unique_key='user_id',
        strategy='check',
        check_cols=['email', 'first_name', 'last_name', 'city', 'street', 'zipcode', 'phone'],
        invalidate_hard_deletes=True
    )
}}

select
    user_id,
    first_name,
    last_name,
    email,
    username,
    city,
    street,
    zipcode,
    phone,
    loaded_at,
    load_date
from {{ ref('stg_users') }}

{% endsnapshot %}