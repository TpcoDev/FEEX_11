DROP TABLE sii_cola_envio CASCADE;
UPDATE account_invoice SET send_queue_id = null WHERE send_queue_id is not null;
UPDATE stock_picking SET send_queue_id = null WHERE send_queue_id is not null;