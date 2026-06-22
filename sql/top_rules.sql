-- Top directional cross-sell rules.
-- The pair table is symmetric; for a recommendation ("customers who buy X also
-- buy Y") direction matters. Here we unfold each qualifying pair into both
-- directions and keep, for each antecedent item, its single strongest rule by
-- confidence using a window function.
-- (PostgreSQL has no QUALIFY, so the ROW_NUMBER() filter is done in an outer query.)

with totals as (
    select count(distinct transaction_id) as n_tx from transaction_items
),

item_counts as (
    select product_id, count(distinct transaction_id) as cnt
    from transaction_items group by product_id
),

pair_counts as (
    select a.product_id as p1, b.product_id as p2,
           count(distinct a.transaction_id) as co_count
    from transaction_items a
    join transaction_items b
        on a.transaction_id = b.transaction_id and a.product_id < b.product_id
    group by a.product_id, b.product_id
),

-- unfold to directional rules antecedent -> consequent
directional as (
    select p1 as ante, p2 as cons, co_count from pair_counts
    union all
    select p2 as ante, p1 as cons, co_count from pair_counts
),

rules as (
    select
        pa.product_name as antecedent,
        pc.product_name as consequent,
        d.co_count,
        round(100.0 * d.co_count / ca.cnt, 1)                   as confidence_pct,
        round((d.co_count * 1.0 * t.n_tx) / (ca.cnt * cc.cnt), 2) as lift
    from directional d
    cross join totals t
    join item_counts ca on ca.product_id = d.ante
    join item_counts cc on cc.product_id = d.cons
    join products pa on pa.product_id = d.ante
    join products pc on pc.product_id = d.cons
    where d.co_count >= 30
),

ranked as (
    select
        rules.*,
        row_number() over (partition by antecedent order by confidence_pct desc) as rn
    from rules
)

select antecedent, consequent, co_count, confidence_pct, lift
from ranked
where rn = 1
order by confidence_pct desc;
