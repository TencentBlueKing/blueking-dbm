-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Add column cluster_alias to tb_k8s_cluster_config
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_config' AND COLUMN_NAME = 'cluster_alias') = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN cluster_alias VARCHAR(32) COMMENT ''k8s 集群名称'' AFTER cluster_name',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
