-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Create unique index on tb_k8s_crd_cluster if not exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND INDEX_NAME = 'unique_cluster_idx') = 0,
    'CREATE UNIQUE INDEX unique_cluster_idx ON tb_k8s_crd_cluster (k8s_cluster_config_id, namespace, cluster_name)',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
