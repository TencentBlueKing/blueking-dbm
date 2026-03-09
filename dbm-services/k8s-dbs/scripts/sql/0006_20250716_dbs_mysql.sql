-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Add column is_public to tb_k8s_cluster_config
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_config' AND COLUMN_NAME = 'is_public') = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN is_public tinyint(1) DEFAULT 1 COMMENT ''是否公有集群,0:私有，1:公有'' AFTER password',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column region_name to tb_k8s_cluster_config
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_config' AND COLUMN_NAME = 'region_name') = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN region_name VARCHAR(32) COMMENT ''区域名称'' AFTER is_public',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column region_code to tb_k8s_cluster_config
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_config' AND COLUMN_NAME = 'region_code') = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN region_code VARCHAR(32) COMMENT ''区域编码'' AFTER region_name',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column provider to tb_k8s_cluster_config
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_config' AND COLUMN_NAME = 'provider') = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN provider VARCHAR(32) COMMENT ''云服务提供商'' AFTER region_code',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
