# Capacity review: Q1 2024

## payments-db

Average connection use is 14 of 50 connections; the peak in January was 31. We recommend reducing the pool to 20 connections, which lets us move to a smaller database instance and save about 1,200 USD per month.

Risk: during unusual peaks requests may wait for a free connection, which would raise checkout latency. We consider this risk low.

## ledger-worker

Two consumers handle the current event volume with headroom. No change recommended.

## Decision

The payments-db pool change is tracked as CHG-2291.
