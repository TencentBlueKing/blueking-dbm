-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Add column bk_biz_id to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'bk_biz_id') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_biz_id int(11) COMMENT ''业务的 cmdb id'' AFTER `namespace`',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column bk_biz_name to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'bk_biz_name') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_biz_name varchar(128) COMMENT ''业务名称'' AFTER `bk_biz_id`',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column bk_app_abbr to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'bk_app_abbr') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_app_abbr VARCHAR(128) COMMENT ''业务名称缩写'' AFTER bk_biz_id',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column bk_app_code to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'bk_app_code') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_app_code VARCHAR(128) COMMENT ''蓝鲸 app 名称'' AFTER bk_app_abbr',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add column cluster_alias to tb_k8s_crd_cluster
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_crd_cluster' AND COLUMN_NAME = 'cluster_alias') = 0,
    'ALTER TABLE tb_k8s_crd_cluster ADD COLUMN cluster_alias varchar(32) COMMENT ''集群别名'' AFTER `cluster_name`',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
