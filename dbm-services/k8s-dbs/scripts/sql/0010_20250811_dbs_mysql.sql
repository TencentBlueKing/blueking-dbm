-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Add column termination_policy to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'termination_policy') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN termination_policy varchar(32) COMMENT ''集群删除策略'' AFTER topo_name',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
