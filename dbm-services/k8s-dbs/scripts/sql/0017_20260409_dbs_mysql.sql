USE bkbase_dbs;
SET NAMES utf8;

-- 为 tb_k8s_cluster_service 表补充 extra 字段
-- 记录 expose 请求中 service 的原始配置（JSON 格式）
SET @col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'bkbase_dbs'
      AND TABLE_NAME   = 'tb_k8s_cluster_service'
      AND COLUMN_NAME  = 'extra'
);

SET @ddl = IF(@col_exists = 0,
    'ALTER TABLE tb_k8s_cluster_service ADD COLUMN extra text NULL COMMENT ''扩展信息, JSON 格式, 记录 expose 请求中 service 的原始配置'' AFTER domains',
    'SELECT ''column extra already exists, skip'''
);

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
