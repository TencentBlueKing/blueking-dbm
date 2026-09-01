-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

-- Create unique index on tb_k8s_cluster_addons if not exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_k8s_cluster_addons' AND INDEX_NAME = 'unique_default_idx') = 0,
    'CREATE UNIQUE INDEX unique_default_idx ON tb_k8s_cluster_addons (addon_id, k8s_cluster_name)',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create unique index on tb_addon_spec_plan if not exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_addon_spec_plan' AND INDEX_NAME = 'unique_default_idx') = 0,
    'CREATE UNIQUE INDEX unique_default_idx ON tb_addon_spec_plan (addon_id, addon_topology, spec_level)',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create unique index on tb_component_spec_plan if not exists
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'tb_component_spec_plan' AND INDEX_NAME = 'unique_default_idx') = 0,
    'CREATE UNIQUE INDEX unique_default_idx ON tb_component_spec_plan (addon_spec_plan_id, component_name)',
    'SELECT 1'
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

