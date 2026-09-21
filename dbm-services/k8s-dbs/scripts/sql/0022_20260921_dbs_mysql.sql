-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Add column bk_biz_id to tb_k8s_cluster_config
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_config' AND COLUMN_NAME = 'bk_biz_id') = 0,
    'ALTER TABLE tb_k8s_cluster_config ADD COLUMN bk_biz_id int(11) COMMENT ''业务的 cmdb id'' AFTER `provider`',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
