USE bkbase_dbs;
SET NAMES utf8;

SET @col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'bkbase_dbs'
      AND TABLE_NAME   = 'tb_k8s_crd_cluster'
      AND COLUMN_NAME  = 'dbm_cluster_id'
);

SET @ddl = IF(@col_exists = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN dbm_cluster_id bigint NULL DEFAULT NULL COMMENT ''DBM 侧集群主键 ID'' AFTER bk_app_code',
    'SELECT ''column dbm_cluster_id already exists, skip'''
);

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
