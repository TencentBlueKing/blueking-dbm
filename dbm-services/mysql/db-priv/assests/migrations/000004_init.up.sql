SET NAMES utf8;
CREATE TABLE IF NOT EXISTS `tb_security_rules` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(200) NOT NULL COMMENT '规则名称',
    `rule` json NOT NULL COMMENT '安全规则',
    `creator` varchar(200) NOT NULL COMMENT '创建者',
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `operator` varchar(200) DEFAULT NULL COMMENT '最后一次变更者',
    `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_name` (`name`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `tb_passwords` (
    `ip` varchar(100) NOT NULL COMMENT '实例ip',
    `port` int unsigned NOT NULL COMMENT '实例端口',
    `bk_cloud_id` int unsigned NOT NULL COMMENT '云区域id',
    `username`  varchar(800) NOT NULL COMMENT '用户名称',
    `password` varchar(800) NOT NULL COMMENT '加密后的密码',
    `component` varchar(100) NOT NULL COMMENT '组件，比如mysql、proxy',
    `lock_until` timestamp COMMENT '锁定到的时间',
    `operator` varchar(200) DEFAULT NULL COMMENT '最后一次变更者',
    `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
    UNIQUE KEY `idx_instance_user` (ip, port, bk_cloud_id, username, component),
    KEY `idx_update_time` (ip, port, bk_cloud_id, username, component,update_time),
    KEY `idx_component`(`component`),
    KEY `idx_bk_cloud_id`(`bk_cloud_id`),
    KEY `idx_lock` (username, component,lock_until,update_time)) ENGINE=InnoDB DEFAULT CHARSET=utf8;
