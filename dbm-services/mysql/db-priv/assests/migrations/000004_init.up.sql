SET NAMES utf8;
CREATE TABLE IF NOT EXISTS `tb_security_rules` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `name` varchar(200) NOT NULL COMMENT '规则名称',
    `rule` json NOT NULL COMMENT '安全规则',
    `creator` varchar(800) NOT NULL COMMENT '创建者',
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `operator` varchar(800) DEFAULT NULL COMMENT '最后一次变更者',
    `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_name` (`name`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `tb_passwords` (
    `ip` varchar(100) NOT NULL COMMENT '实例ip',
    `port` int unsigned NOT NULL COMMENT '实例端口',
    `password` varchar(800) NOT NULL COMMENT '加密后的密码',
    `username`  varchar(800) NOT NULL COMMENT '用户名称',
    `lock_until` timestamp COMMENT '锁定到的时间',
    `operator` varchar(800) DEFAULT NULL COMMENT '最后一次变更者',
    `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
    UNIQUE KEY `idx_ip_port` (ip, port, username),
    KEY `idx_lock` (`lock_until`)) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `tb_randomize_exclude` (
    `username` varchar(800) NOT NULL COMMENT '用户名称',
    `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
    `operator` varchar(800) DEFAULT NULL COMMENT '最后一次变更者',
    `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
    UNIQUE KEY `idx_username_bk_biz_id` (username, bk_biz_id)) ENGINE=InnoDB DEFAULT CHARSET=utf8;

