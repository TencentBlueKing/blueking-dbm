SET NAMES utf8;
CREATE TABLE IF NOT EXISTS `mysql_partition_config` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `bk_biz_id` int NOT NULL,
    `immute_domain` varchar(200) NOT NULL,
    `port` int NOT NULL,
    `bk_cloud_id` int NOT NULL,
    `cluster_id` int NOT NULL,
    `dblike` varchar(100) NOT NULL,
    `tblike` varchar(100) NOT NULL,
    `partition_column` varchar(100) DEFAULT NULL,
    `partition_column_type` varchar(100) DEFAULT NULL,
    `reserved_partition` int NOT NULL,
    `extra_partition` int NOT NULL,
    `partition_time_interval` int NOT NULL,
    `partition_type` int NOT NULL,
    `expire_time` int NOT NULL,
    `time_zone`  varchar(16) NOT NULL COMMENT '集群所在的时区',
    `creator` varchar(100) DEFAULT NULL,
    `updator` varchar(100) DEFAULT NULL,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00',
    `phase` varchar(100) NOT NULL COMMENT 'online--在用;offline--停用',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq` (`bk_biz_id`,`immute_domain`,`cluster_id`,`dblike`,`tblike`),
    KEY `idx_time_zone_phase` (`cluster_id`,`time_zone`,`phase`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `spider_partition_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `bk_biz_id` int NOT NULL,
  `immute_domain` varchar(200) NOT NULL,
  `port` int NOT NULL,
  `bk_cloud_id` int NOT NULL,
  `cluster_id` int NOT NULL,
  `dblike` varchar(100) NOT NULL,
  `tblike` varchar(100) NOT NULL,
  `partition_column` varchar(100) DEFAULT NULL,
  `partition_column_type` varchar(100) DEFAULT NULL,
  `reserved_partition` int NOT NULL,
  `extra_partition` int NOT NULL,
  `partition_time_interval` int NOT NULL,
  `partition_type` int NOT NULL,
  `expire_time` int NOT NULL,
  `time_zone`  varchar(16) NOT NULL COMMENT '集群所在的时区',
  `creator` varchar(100) DEFAULT NULL,
  `updator` varchar(100) DEFAULT NULL,
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00',
  `phase` varchar(100) NOT NULL COMMENT 'online--在用;offline--停用',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq` (`bk_biz_id`,`immute_domain`,`cluster_id`,`dblike`,`tblike`),
  KEY `idx_time_zone_phase` (`cluster_id`,`time_zone`,`phase`)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `mysql_partition_cron_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `config_id` int NOT NULL,
  `bk_biz_id` int NOT NULL,
  `cluster_id` int NOT NULL,
  `ticket_id` int NOT NULL,
  `immute_domain` varchar(200) NOT NULL,
  `scheduler` varchar(100) NOT NULL,
  `bk_cloud_id` int NOT NULL,
  `time_zone` varchar(100) NOT NULL,
  `cron_date` varchar(100) NOT NULL,
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `check_info` text,
  `status` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_cron_date_status` (cron_date,status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `spider_partition_cron_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `config_id` int NOT NULL,
  `bk_biz_id` int NOT NULL,
  `cluster_id` int NOT NULL,
  `ticket_id` int NOT NULL,
  `immute_domain` varchar(200) NOT NULL,
  `scheduler` varchar(100) NOT NULL,
  `bk_cloud_id` int NOT NULL,
  `time_zone` varchar(100) NOT NULL,
  `cron_date` varchar(100) NOT NULL,
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `check_info` text,
  `status` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_create_time` (`create_time`),
  KEY `idx_cron_date_status` (cron_date,status)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `manage_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config_id` int(11) NOT NULL,
  `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
  `operator` varchar(800) NOT NULL COMMENT '操作者',
  `para` longtext NOT NULL COMMENT '参数',
  `execute_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
  PRIMARY KEY (`id`),
  KEY `bk_biz_id` (`bk_biz_id`,`config_id`,`operator`(10),`execute_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `version` bigint(20) NOT NULL,
  `dirty` tinyint(1) NOT NULL,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
