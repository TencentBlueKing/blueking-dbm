USE bkbase_dbs;
SET NAMES utf8;

-- Drop index addon_name on tb_k8s_crd_storageaddon if exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_storageaddon' AND INDEX_NAME = 'addon_name') > 0,
    'ALTER TABLE tb_k8s_crd_storageaddon DROP INDEX addon_name',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
