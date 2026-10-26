# ledger-worker postmortem (INC-0412)

## What happened

ledger-worker writes every confirmed payment to the ledger. On 14 March its consumer lag grew while checkout-api retried slow requests, and peaked at 41 minutes. About 2,300 payments reached the ledger late. Balances shown to merchants were behind during that time.

## Why the lag grew

Retries from checkout-api published duplicate payment events. ledger-worker discards duplicates, but each one still costs a database round trip on the already exhausted payments-db pool.

## What we change

- Deduplicate events before they reach the database.
- Alert when consumer lag passes 10 minutes.
