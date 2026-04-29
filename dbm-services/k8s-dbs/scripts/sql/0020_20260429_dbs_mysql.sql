USE bkbase_dbs;
SET NAMES utf8;

-- 为 tb_k8s_cluster_config 表补充 vpc_id 字段
-- dbm 单据 ID
SET @col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'bkbase_dbs'
      AND TABLE_NAME   = 'tb_k8s_cluster_config'
      AND COLUMN_NAME  = 'vpc_id'
);

SET @ddl = IF(@col_exists = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN vpc_id VARCHAR(32) DEFAULT NULL COMMENT ''k8s 集群所属 vpc'' AFTER region_code',
    'SELECT ''column extra already exists, skip'''
);

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
