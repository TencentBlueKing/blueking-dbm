SET NAMES utf8;
CREATE TABLE IF NOT EXISTS `mysql_manage_logs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `config_id` int(11) NOT NULL,
    `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
    `operate` varchar(255) NOT NULL COMMENT '操作类型',
    `operator` varchar(800) NOT NULL COMMENT '操作者',
    `para` longtext NOT NULL COMMENT '参数',
    `execute_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    PRIMARY KEY (`id`),
    KEY `bk_biz_id` (`bk_biz_id`,`config_id`,`operator`(10),`execute_time`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
CREATE TABLE IF NOT EXISTS `spider_manage_logs` (
    `id` int(11) NOT NULL AUTO_INCREMENT,
    `config_id` int(11) NOT NULL,
    `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
    `operate` varchar(255) NOT NULL COMMENT '操作类型',
    `operator` varchar(800) NOT NULL COMMENT '操作者',
    `para` longtext NOT NULL COMMENT '参数',
    `execute_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
    PRIMARY KEY (`id`),
    KEY `bk_biz_id` (`bk_biz_id`,`config_id`,`operator`(10),`execute_time`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
DROP TABLE IF EXISTS manage_logs;
