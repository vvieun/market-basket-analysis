-- Item support: in what share of baskets does each product appear?
-- support(item) = transactions containing the item / total transactions.

with totals as (
    select count(distinct transaction_id) as n_tx
    from transaction_items
)

select
    p.product_name,
    p.category,
    count(distinct ti.transaction_id)                          as n_baskets,
    round(100.0 * count(distinct ti.transaction_id) / t.n_tx, 2) as support_pct
from transaction_items ti
join products p using (product_id)
cross join totals t
group by p.product_name, p.category, t.n_tx
order by n_baskets desc;
