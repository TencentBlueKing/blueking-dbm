DROP VIEW IF EXISTS `v_tb_config_node_plat`;

CREATE ALGORITHM = UNDEFINED SQL SECURITY DEFINER VIEW `v_tb_config_node_plat` AS
select
    0 AS `id`,
    '0' AS `bk_biz_id`,
    `tb_config_name_def`.`namespace` AS `namespace`,
    `tb_config_name_def`.`conf_type` AS `conf_type`,
    `tb_config_name_def`.`conf_file` AS `conf_file`,
    `tb_config_name_def`.`conf_name` AS `conf_name`,
    'plat' AS `level_name`,
    '0' AS `level_value`,
    '' AS `updated_revision`,
    `tb_config_name_def`.`value_default` AS `conf_value`,
    `tb_config_name_def`.`flag_locked` AS `flag_locked`,
    `tb_config_name_def`.`flag_disable` AS `flag_disable`,
    `tb_config_name_def`.`flag_status` AS `flag_status`,
    `tb_config_name_def`.`stage` AS `stage`,
    `tb_config_name_def`.`conf_name_lc` AS `description`,
    `tb_config_name_def`.`created_at` AS `created_at`,
    `tb_config_name_def`.`updated_at` AS `updated_at`
from
    `tb_config_name_def`
where
    (`tb_config_name_def`.`flag_status` >0)