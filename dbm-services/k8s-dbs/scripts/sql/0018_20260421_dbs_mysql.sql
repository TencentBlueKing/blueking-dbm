USE bkbase_dbs;
SET NAMES utf8;

-- 为 tb_cluster_request_record 表补充 ticket_id 字段
-- dbm 单据 ID
SET @col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'bkbase_dbs'
      AND TABLE_NAME   = 'tb_cluster_request_record'
      AND COLUMN_NAME  = 'ticket_id'
);

SET @ddl = IF(@col_exists = 0,
    'ALTER TABLE tb_cluster_request_record ADD COLUMN ticket_id INT NULL COMMENT ''dbm 单据 ID'' AFTER description',
    'SELECT ''column extra already exists, skip'''
);

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
