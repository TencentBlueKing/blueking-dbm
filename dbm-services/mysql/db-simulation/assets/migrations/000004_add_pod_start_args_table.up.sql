CREATE TABLE IF NOT EXISTS `tb_mysql_pod_start_cfgs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `component_type` varchar(64) NOT NULL,
    `version` varchar(64) NOT NULL,
    `start_args` varchar(1024) NOT NULL,
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_cv` (`component_type`, `version`)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;