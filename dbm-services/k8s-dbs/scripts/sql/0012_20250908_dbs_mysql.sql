USE bkbase_dbs;
SET NAMES utf8;

-- Add column completed_at to tb_k8s_crd_opsrequest
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_opsrequest' AND COLUMN_NAME = 'completed_at') = 0,
    'ALTER TABLE tb_k8s_crd_opsrequest ADD COLUMN completed_at timestamp NULL DEFAULT NULL COMMENT ''操作结束时间'' AFTER status',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
