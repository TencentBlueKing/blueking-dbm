DROP TABLE IF EXISTS `tb_config_name_def`;
CREATE TABLE `tb_config_name_def` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `namespace` varchar(100) DEFAULT NULL,
  `conf_type` varchar(100) DEFAULT NULL,
  `conf_file` varchar(100) DEFAULT NULL,
  `conf_name` varchar(100) NOT NULL,
  `value_type` varchar(100) NOT NULL DEFAULT 'STRING' COMMENT 'STRING,INT,FLOAT,NUMBER',
  `value_default` text,
  `value_allowed` text,
  `value_type_sub` varchar(100) NOT NULL DEFAULT '' COMMENT 'STRING,ENUM,RANGE,REGEX,JSON,COMPLEX',
  `flag_readonly` tinyint(4) DEFAULT '0',
  `flag_visible` tinyint(4) DEFAULT '1',
  `flag_status` tinyint(4) NOT NULL COMMENT '1: 显式的公共配置 -1:不会显式出现在配置文件的全量配置项, 2: 显式的公共配置且只读',
  `flag_disable` tinyint(4) NOT NULL DEFAULT '0' COMMENT '2:readonly, 1:disable, 0:enable, -2: not_allowed_given, -3:must_given',
  `flag_locked` tinyint(4) NOT NULL DEFAULT '0',
  `flag_encrypt` tinyint(4) NOT NULL DEFAULT '0',
  `need_restart` tinyint(4) NOT NULL DEFAULT '1',
  `value_formula` varchar(200) DEFAULT NULL,
  `extra_info` varchar(200) DEFAULT NULL,
  `conf_name_lc` varchar(100) DEFAULT NULL,
  `order_index` int(11) DEFAULT '-1' COMMENT '-1: 无序',
  `since_version` varchar(100) DEFAULT NULL COMMENT 'conf_name allowed since version xxx',
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `stage` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_ns_type_file_name` (`namespace`,`conf_type`,`conf_file`,`conf_name`)
) ENGINE=InnoDB AUTO_INCREMENT=70919 DEFAULT CHARSET=utf8;

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
    `tb_config_name_def`.`flag_visible` AS `flag_visible`,
    `tb_config_name_def`.`flag_readonly` AS `flag_readonly`,
    `tb_config_name_def`.`stage` AS `stage`,
    `tb_config_name_def`.`conf_name_lc` AS `description`,
    `tb_config_name_def`.`created_at` AS `created_at`,
    `tb_config_name_def`.`updated_at` AS `updated_at`
from
    `tb_config_name_def`
where
    (`tb_config_name_def`.`flag_visible` =1)