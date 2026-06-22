-- Association rules for product pairs: support, confidence and lift.
--
-- For an unordered pair {A, B}:
--   support(A,B)    = baskets with both A and B / N
--   confidence(A→B) = baskets with both / baskets with A
--   lift(A,B)       = support(A,B) / (support(A) * support(B))
--                   = co_count * N / (count_A * count_B)
--
-- lift > 1  => bought together more than chance (complements)
-- lift ~ 1  => independent
-- lift < 1  => substitutes / rarely together
--
-- Demonstrates: self-join on the basket grain with a.product_id < b.product_id
-- to get each unordered pair once, COUNT(DISTINCT), and a final lift formula.

with totals as (
    select count(distinct transaction_id) as n_tx from transaction_items
),

item_counts as (
    select product_id, count(distinct transaction_id) as cnt
    from transaction_items
    group by product_id
),

pair_counts as (                       -- co-occurrence per unordered pair
    select
        a.product_id as product_a,
        b.product_id as product_b,
        count(distinct a.transaction_id) as co_count
    from transaction_items a
    join transaction_items b
        on a.transaction_id = b.transaction_id
       and a.product_id < b.product_id   -- each pair once, no self-pairs
    group by a.product_id, b.product_id
)

select
    pa.product_name as item_a,
    pb.product_name as item_b,
    pc.co_count,
    round(100.0 * pc.co_count / t.n_tx, 2)                       as support_pct,
    round(100.0 * pc.co_count / ca.cnt, 1)                       as conf_a_to_b_pct,
    round(100.0 * pc.co_count / cb.cnt, 1)                       as conf_b_to_a_pct,
    round((pc.co_count * 1.0 * t.n_tx) / (ca.cnt * cb.cnt), 2)   as lift
from pair_counts pc
cross join totals t
join item_counts ca on ca.product_id = pc.product_a
join item_counts cb on cb.product_id = pc.product_b
join products pa on pa.product_id = pc.product_a
join products pb on pb.product_id = pc.product_b
where pc.co_count >= 30          -- min support filter: ignore rare, noisy pairs
order by lift desc;
