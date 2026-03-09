-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Add column service_version to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'service_version') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN service_version varchar(32) COMMENT ''引擎具体版本'' AFTER addoncluster_version',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
