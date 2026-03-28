{% snapshot products_snapshot %}

{{
    config(
        target_schema='MARTS',
        unique_key='product_id',
        strategy='check',
        check_cols=['price', 'category', 'rating_score', 'rating_count'],
        invalidate_hard_deletes=True
    )
}}

select
    product_id,
    product_name,
    category,
    price,
    description,
    image_url,
    rating_score,
    rating_count,
    loaded_at,
    load_date
from {{ ref('stg_products') }}

{% endsnapshot %}