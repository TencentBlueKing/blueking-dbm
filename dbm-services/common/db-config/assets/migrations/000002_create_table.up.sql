-- MySQL dump 10.13  Distrib 5.7.20, for Linux (x86_64)
--
-- Host: localhost    Database: bk_dbconfig
-- ------------------------------------------------------
-- Server version	5.7.20-tmysql-3.3-log
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
-- Table structure for table `schema_migrations`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `schema_migrations` (
  `version` bigint(20) NOT NULL,
  `dirty` tinyint(1) NOT NULL,
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_file_def`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_file_def` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `namespace` varchar(100) DEFAULT NULL,
  `conf_type` varchar(100) NOT NULL,
  `conf_file` varchar(100) DEFAULT NULL,
  `conf_type_lc` varchar(100) DEFAULT NULL,
  `conf_file_lc` varchar(100) DEFAULT NULL,
  `level_names` varchar(100) DEFAULT NULL,
  `level_versioned` varchar(100) DEFAULT NULL,
  `conf_name_validate` tinyint(4) NOT NULL DEFAULT '1',
  `conf_value_validate` tinyint(4) NOT NULL DEFAULT '1',
  `value_type_strict` tinyint(4) DEFAULT '0' COMMENT 'convert value to value_type for resp',
  `namespace_info` varchar(100) DEFAULT NULL,
  `version_keep_limit` int(11) DEFAULT '5',
  `version_keep_days` int(11) DEFAULT '365',
  `conf_name_order` tinyint(4) DEFAULT '0' COMMENT '-1,0: no order',
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tb_config_type_def_UN` (`namespace`,`conf_type`,`conf_file`)
) ENGINE=InnoDB AUTO_INCREMENT=202 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_file_node`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_file_node` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `namespace` varchar(100) NOT NULL,
  `bk_biz_id` varchar(100) NOT NULL,
  `conf_type` varchar(100) NOT NULL,
  `conf_file` varchar(100) NOT NULL DEFAULT '',
  `level_name` varchar(100) NOT NULL,
  `level_value` varchar(120) NOT NULL,
  `conf_type_lc` varchar(100) DEFAULT NULL,
  `conf_file_lc` varchar(100) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_by` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_level_node` (`namespace`,`bk_biz_id`,`conf_file`,`conf_type`,`level_name`,`level_value`)
) ENGINE=InnoDB AUTO_INCREMENT=490 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_level_def`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_level_def` (
  `level_name` varchar(60) NOT NULL,
  `level_priority` int(11) NOT NULL,
  `level_name_cn` varchar(100) DEFAULT NULL,
  `description` varchar(255) DEFAULT '',
  `flag_disable` tinyint(4) DEFAULT '0',
  PRIMARY KEY (`level_priority`),
  UNIQUE KEY `un_level_name` (`level_name`),
  KEY `idx_level` (`level_priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_name_def`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_name_def` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `namespace` varchar(100) DEFAULT NULL,
  `conf_type` varchar(100) DEFAULT NULL,
  `conf_file` varchar(100) DEFAULT NULL,
  `conf_name` varchar(100) NOT NULL,
  `value_type` varchar(100) NOT NULL DEFAULT 'STRING' COMMENT 'STRING,INT,FLOAT,NUMBER',
  `value_default` text,
  `value_allowed` text,
  `value_type_sub` varchar(100) NOT NULL DEFAULT '' COMMENT 'STRING,ENUM,RANGE,REGEX,JSON,COMPLEX',
  `flag_status` tinyint(4) NOT NULL DEFAULT '0' COMMENT '1: 显式的公共配置 0:不会显式出现在配置文件的全量配置项, 2: 显式的公共配置且只读',
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
) ENGINE=InnoDB AUTO_INCREMENT=15919 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_node`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_node` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `node_id` int(11) DEFAULT NULL,
  `bk_biz_id` varchar(100) NOT NULL,
  `namespace` varchar(100) DEFAULT NULL COMMENT 'service.service_role',
  `conf_type` varchar(60) NOT NULL DEFAULT '',
  `conf_file` varchar(60) NOT NULL,
  `conf_name` varchar(60) NOT NULL,
  `conf_value` text,
  `level_name` varchar(60) NOT NULL,
  `level_value` varchar(120) DEFAULT 'pub',
  `flag_locked` tinyint(4) NOT NULL DEFAULT '0',
  `flag_disable` tinyint(4) DEFAULT '0' COMMENT '-1: deleted 0:enable, 1:disable, -2: not_allowed',
  `description` varchar(255) DEFAULT '',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `updated_revision` varchar(60) DEFAULT NULL,
  `stage` tinyint(4) NOT NULL DEFAULT '0' COMMENT 'conf_value 里的值状态，0: 仅保存未发布, 1:已发布未应用, 2: 已应用',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uni_pri` (`bk_biz_id`,`namespace`,`conf_type`,`conf_file`,`level_name`,`level_value`,`conf_name`)
) ENGINE=InnoDB AUTO_INCREMENT=23398 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_node_task`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_node_task` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `node_id` int(10) unsigned NOT NULL,
  `version_id` int(10) unsigned NOT NULL,
  `revision` varchar(100) NOT NULL,
  `conf_name` varchar(100) NOT NULL,
  `conf_value` varchar(255) DEFAULT NULL,
  `value_before` varchar(255) DEFAULT NULL,
  `op_type` varchar(100) NOT NULL DEFAULT '',
  `updated_revision` varchar(100) NOT NULL,
  `stage` tinyint(4) NOT NULL COMMENT '1: new, 2:applied',
  `flag_locked` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_node_conf` (`node_id`,`conf_name`)
) ENGINE=InnoDB AUTO_INCREMENT=490 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tb_config_versioned`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_config_versioned` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `node_id` int(11) DEFAULT NULL,
  `bk_biz_id` varchar(100) DEFAULT NULL,
  `conf_type` varchar(100) DEFAULT NULL,
  `namespace` varchar(100) DEFAULT NULL,
  `level_name` varchar(100) DEFAULT NULL,
  `level_value` varchar(100) DEFAULT NULL,
  `conf_file` varchar(100) DEFAULT NULL,
  `revision` varchar(100) DEFAULT NULL,
  `content_str` mediumtext,
  `content_md5` varchar(60) DEFAULT NULL,
  `content_obj` text,
  `is_published` tinyint(1) DEFAULT '0' COMMENT '0:未发布, 1:发布, -1:未发布但层级发布过',
  `is_applied` tinyint(1) DEFAULT '0' COMMENT '0:未应用, 1:已应用',
  `module` varchar(100) DEFAULT NULL,
  `cluster` varchar(100) DEFAULT NULL,
  `pre_revision` varchar(100) DEFAULT NULL,
  `rows_affected` int(11) NOT NULL DEFAULT '0',
  `content_obj_diff` text,
  `description` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_by` varchar(60) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_node_revision` (`bk_biz_id`,`namespace`,`conf_type`,`conf_file`,`level_name`,`level_value`,`revision`),
  UNIQUE KEY `uniq_nodeid_revision` (`node_id`,`revision`)
) ENGINE=InnoDB AUTO_INCREMENT=4514 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Temporary table structure for view `v_tb_config_node_plat`
--

SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8;
/*!50001 CREATE VIEW `v_tb_config_node_plat` AS SELECT 
 1 AS `id`,
 1 AS `bk_biz_id`,
 1 AS `namespace`,
 1 AS `conf_type`,
 1 AS `conf_file`,
 1 AS `conf_name`,
 1 AS `level_name`,
 1 AS `level_value`,
 1 AS `updated_revision`,
 1 AS `conf_value`,
 1 AS `flag_locked`,
 1 AS `flag_disable`,
 1 AS `flag_status`,
 1 AS `stage`,
 1 AS `description`,
 1 AS `created_at`,
 1 AS `updated_at`*/;
SET character_set_client = @saved_cs_client;

--
-- Final view structure for view `v_tb_config_node_plat`
--

/*!50001 DROP VIEW IF EXISTS `v_tb_config_node_plat`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8 */;
/*!50001 SET character_set_results     = utf8 */;
/*!50001 SET collation_connection      = utf8_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50001 VIEW `v_tb_config_node_plat` AS select 0 AS `id`,'0' AS `bk_biz_id`,`tb_config_name_def`.`namespace` AS `namespace`,`tb_config_name_def`.`conf_type` AS `conf_type`,`tb_config_name_def`.`conf_file` AS `conf_file`,`tb_config_name_def`.`conf_name` AS `conf_name`,'plat' AS `level_name`,'0' AS `level_value`,'' AS `updated_revision`,`tb_config_name_def`.`value_default` AS `conf_value`,`tb_config_name_def`.`flag_locked` AS `flag_locked`,`tb_config_name_def`.`flag_disable` AS `flag_disable`,`tb_config_name_def`.`flag_status` AS `flag_status`,`tb_config_name_def`.`stage` AS `stage`,`tb_config_name_def`.`conf_name_lc` AS `description`,`tb_config_name_def`.`created_at` AS `created_at`,`tb_config_name_def`.`updated_at` AS `updated_at` from `tb_config_name_def` where (`tb_config_name_def`.`flag_status` > 0) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-03-28 21:09:08
