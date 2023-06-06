-- MySQL dump 10.13  Distrib 5.7.20, for Linux (x86_64)
--
-- Host: localhost    Database: bk_dbpriv
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
-- Table structure for table `priv_logs`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `priv_logs` (
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
-- Dumping data for table `priv_logs`
--


--
-- Table structure for table `tb_account_rules`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_account_rules` (
                                    `id` int(11) NOT NULL AUTO_INCREMENT,
                                    `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
                                    `cluster_type` varchar(800) NOT NULL COMMENT '账号规则适用的集群类型',
                                    `account_id` int(11) NOT NULL COMMENT 'tb_accounts表的id',
                                    `dbname` varchar(800) NOT NULL COMMENT '访问db',
                                    `priv` varchar(800) NOT NULL COMMENT '访问权限',
                                    `dml_ddl_priv` varchar(800) NOT NULL COMMENT 'DML,DDL访问权限',
                                    `global_priv` varchar(800) NOT NULL COMMENT 'GLOBAL访问权限',
                                    `creator` varchar(800) NOT NULL COMMENT '创建者',
                                    `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                                    `operator` varchar(800) DEFAULT NULL COMMENT '最后一次变更者',
                                    `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
                                    `priv_type` varchar(3) DEFAULT NULL,
                                    PRIMARY KEY (`id`),
                                    UNIQUE KEY `bk_biz_id` (`bk_biz_id`,`account_id`,`dbname`),
                                    KEY `account_id` (`account_id`),
                                    CONSTRAINT `tb_account_rules_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `tb_accounts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='账号规则配置';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_account_rules`
--


--
-- Table structure for table `tb_accounts`
--

/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS `tb_accounts` (
                               `id` int(11) NOT NULL AUTO_INCREMENT,
                               `bk_biz_id` int(11) NOT NULL COMMENT '业务的 cmdb id',
                               `cluster_type` varchar(800) NOT NULL COMMENT '账号适用的集群类型',
                               `user` varchar(200) NOT NULL COMMENT '用户名',
                               `psw` json NOT NULL COMMENT '密码',
                               `creator` varchar(800) NOT NULL COMMENT '创建者',
                               `create_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                               `operator` varchar(800) DEFAULT NULL COMMENT '最后一次变更者',
                               `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后一次变更时间',
                               PRIMARY KEY (`id`),
                               UNIQUE KEY `bk_biz_id` (`bk_biz_id`,`user`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tb_accounts`
--

/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-01-04 10:12:39
