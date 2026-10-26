# Change log: March 2024

## CHG-2288 (5 Mar 2024, 13:00 UTC)

Service: notification-service. Receipt emails are retried up to three times. Owner: Growth team.

## CHG-2291 (14 Mar 2024, 09:40 UTC)

Service: payments-db. Connection pool reduced from 50 to 20 connections, as recommended by the Q1 capacity review. Owner: Platform Data team. Reverted on 14 Mar 2024 during INC-0412.

## CHG-2294 (14 Mar 2024, 08:55 UTC)

Service: checkout-api. Calls to fraud-scoring time out after 3 seconds instead of 5, with one retry. Owner: Risk team.

## CHG-2301 (21 Mar 2024, 10:00 UTC)

Service: auth-service. Session tokens expire after 15 minutes instead of 30. Owner: Identity team.

## CHG-2305 (22 Mar 2024, 15:30 UTC)

Service: payments-db. Connection pool set to 40 connections after a load test. Owner: Platform Data team.
