CREATE TABLE IF NOT EXISTS `tb_container_records` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `uid` varchar(255) NOT NULL,
    `container` varchar(255) NOT NULL,
    `create_pod_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `pod_ready_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE IF NOT EXISTS `tb_request_records` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `request_id` varchar(64) NOT NULL,
    `request_body` json DEFAULT NULL,
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `method` varchar(16) NOT NULL,
    `user` varchar(32) NOT NULL,
    `path` varchar(32) NOT NULL,
    `source_ip` varchar(32) NOT NULL,
    `response_code` int(11) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `request_id` (`request_id`)
) ENGINE = InnoDB AUTO_INCREMENT = 77006 DEFAULT CHARSET = utf8mb4;
CREATE TABLE IF NOT EXISTS `tb_simulation_img_cfgs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `component_type` varchar(64) NOT NULL,
    `version` varchar(64) NOT NULL,
    `image` varchar(128) NOT NULL,
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `component_type` (`component_type`),
    UNIQUE KEY `version` (`version`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE IF NOT EXISTS `tb_simulation_tasks` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `task_id` varchar(256) NOT NULL,
    `request_id` varchar(64) NOT NULL,
    `phase` varchar(16) NOT NULL,
    `status` varchar(16) NOT NULL,
    `stdout` mediumtext,
    `stderr` mediumtext,
    `sys_err_msg` text,
    `extra` varchar(512) NOT NULL,
    `heartbeat_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `bill_task_id` varchar(128) NOT NULL,
    `mysql_version` varchar(64) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `task_id` (`task_id`),
    UNIQUE KEY `request_id` (`request_id`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE IF NOT EXISTS `tb_sql_file_simulation_infos` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `task_id` varchar(128) NOT NULL,
    `file_name_hash` varchar(65) DEFAULT NULL,
    `file_name` text NOT NULL,
    `status` varchar(16) NOT NULL,
    `err_msg` varchar(512) NOT NULL,
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `bill_task_id` varchar(128) NOT NULL,
    `line_id` int(11) NOT NULL,
    `mysql_version` varchar(64) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_tk_file` (`task_id`, `file_name_hash`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
CREATE TABLE IF NOT EXISTS `tb_syntax_rules` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `group_name` varchar(64) NOT NULL,
    `rule_name` varchar(64) NOT NULL,
    `item` varchar(1024) NOT NULL,
    `item_type` varchar(128) NOT NULL,
    `expr` varchar(128) NOT NULL,
    `desc` varchar(512) NOT NULL,
    `warn_level` smallint(2) NOT NULL,
    `status` tinyint(1) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `group` (`group_name`, `rule_name`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;