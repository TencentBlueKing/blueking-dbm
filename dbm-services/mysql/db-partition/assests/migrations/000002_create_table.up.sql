-- MySQL dump 10.13  Distrib 5.7.20, for Linux (x86_64)
--
-- Host: localhost  Database: dbpartition
-- ------------------------------------------------------
-- Server version	5.7.20-tmysql-3.3.2-log
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!50717 SELECT COUNT(*) INTO @rocksdb_has_p_s_session_variables FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'performance_schema' AND TABLE_NAME = 'session_variables' */;
/*!50717 SET @rocksdb_get_is_supported = IF (@rocksdb_has_p_s_session_variables, 'SELECT COUNT(*) INTO @rocksdb_is_supported FROM performance_schema.session_variables WHERE VARIABLE_NAME=\'rocksdb_bulk_load\'', 'SELECT 0') */;
/*!50717 PREPARE s FROM @rocksdb_get_is_supported */;
/*!50717 EXECUTE s */;
/*!50717 DEALLOCATE PREPARE s */;
/*!50717 SET @rocksdb_enable_bulk_load = IF (@rocksdb_is_supported, 'SET SESSION rocksdb_bulk_load = 1', 'SET @rocksdb_dummy_bulk_load = 0') */;
/*!50717 PREPARE s FROM @rocksdb_enable_bulk_load */;
/*!50717 EXECUTE s */;
/*!50717 DEALLOCATE PREPARE s */;

--
-- Table structure for table `mysql_partition_config`
--

/*!40101 SET @saved_cs_client   = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
    `creator` varchar(100) DEFAULT NULL,
    `updator` varchar(100) DEFAULT NULL,
    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `update_time` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00',
    `phase` varchar(100) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uniq` (`bk_biz_id`,`immute_domain`,`cluster_id`,`dblike`,`tblike`),
    KEY `idx_cluster_id_phase` (`cluster_id`,`phase`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `spider_partition_config`
--

/*!40101 SET @saved_cs_client   = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
  `creator` varchar(100) DEFAULT NULL,
  `updator` varchar(100) DEFAULT NULL,
  `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00',
  `phase` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq` (`bk_biz_id`,`immute_domain`,`cluster_id`,`dblike`,`tblike`),
  KEY `idx_cluster_id_phase` (`cluster_id`,`phase`)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;


--
-- Table structure for table `mysql_partition_cron_log`
--

/*!40101 SET @saved_cs_client   = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
  `ticket_detail` json DEFAULT NULL,
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `check_info` text,
  `status` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_create_time` (`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mysql_partition_cron_log`
--

/*!40101 SET @saved_cs_client   = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
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
  `ticket_detail` json DEFAULT NULL,
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `check_info` text,
  `status` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_create_time` (`create_time`)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `partition_logs`
--

/*!40101 SET @saved_cs_client   = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `partition_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
  `operator` varchar(800) NOT NULL COMMENT '操作者',
  `para` longtext NOT NULL COMMENT '参数',
  `execute_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '执行时间',
  PRIMARY KEY (`id`),
  KEY `bk_biz_id` (`bk_biz_id`,`operator`(10),`execute_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `schema_migrations`
--

/*!40101 SET @saved_cs_client   = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `version` bigint(20) NOT NULL,
  `dirty` tinyint(1) NOT NULL,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;


/*!40101 SET character_set_client = @saved_cs_client */;
/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-03-22 20:55:00
