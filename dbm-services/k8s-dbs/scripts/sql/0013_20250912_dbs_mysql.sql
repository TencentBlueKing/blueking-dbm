USE bkbase_dbs;
SET NAMES utf8;

-- Drop index k8s_cluster_name on tb_k8s_cluster_addons if exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_addons' AND INDEX_NAME = 'k8s_cluster_name') > 0,
    'ALTER TABLE tb_k8s_cluster_addons DROP INDEX k8s_cluster_name',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
