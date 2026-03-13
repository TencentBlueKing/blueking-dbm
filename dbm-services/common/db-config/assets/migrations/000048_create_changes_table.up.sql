-- bk_dbconfig_data.tb_conf_item_changes definition

CREATE TABLE IF NOT EXISTS `tb_conf_item_changes` (
    `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
    `bk_biz_id` varchar(100) DEFAULT NULL,
    `namespace` varchar(120) NOT NULL DEFAULT '' COMMENT '命名空间',
    `conf_type` varchar(60) NOT NULL DEFAULT '' COMMENT '配置类型',
    `conf_file` varchar(120) NOT NULL DEFAULT '' COMMENT '配置文件',
    `conf_name` varchar(120) NOT NULL COMMENT '配置项名称',
    `level_name` varchar(120) NOT NULL COMMENT '层级名称',
    `level_value` varchar(120) NOT NULL DEFAULT '' COMMENT '层级值',
    `before_image` varchar(255) NOT NULL DEFAULT '' COMMENT '变更前快照（JSON）',
    `after_image` varchar(255) NOT NULL DEFAULT '' COMMENT '变更后快照（JSON）',
    `op_user` varchar(120) NOT NULL DEFAULT '' COMMENT '操作人',
    `op_type` varchar(60) NOT NULL DEFAULT '' COMMENT '操作类型（add/update/remove）',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_conf_key` (`namespace`,`conf_file`,`conf_type`,`conf_name`),
    KEY `idx_level_name` (`level_name`,`level_value`),
    KEY `idx_level_value` (`bk_biz_id`,`level_value`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COMMENT='配置项变更记录表';

-- bk_dbconfig_data.tb_conf_name_changes definition

CREATE TABLE IF NOT EXISTS `tb_conf_name_changes` (
    `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键',
    `namespace` varchar(120) NOT NULL DEFAULT '' COMMENT '命名空间',
    `conf_type` varchar(60) NOT NULL DEFAULT '' COMMENT '配置类型',
    `conf_file` varchar(120) NOT NULL DEFAULT '' COMMENT '配置文件',
    `conf_name` varchar(120) NOT NULL COMMENT '配置项名称',
    `before_image` varchar(255) NOT NULL DEFAULT '' COMMENT '变更前快照（JSON）',
    `after_image` varchar(255) NOT NULL DEFAULT '' COMMENT '变更后快照（JSON）',
    `op_user` varchar(120) NOT NULL DEFAULT '' COMMENT '操作人',
    `op_type` varchar(60) NOT NULL DEFAULT '' COMMENT '操作类型（add/update/remove）',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    KEY `idx_conf_key` (`namespace`,`conf_type`,`conf_file`,`conf_name`),
    KEY `idx_conf_file` (`conf_file`, `namespace`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COMMENT='配置项定义变更记录表';