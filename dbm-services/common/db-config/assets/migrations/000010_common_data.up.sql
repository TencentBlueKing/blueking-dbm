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
-- Dumping data for table `tb_config_file_def`
--
-- WHERE:  namespace='common'

INSERT INTO `tb_config_file_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_type_lc`, `conf_file_lc`, `level_names`, `level_versioned`, `conf_name_validate`, `conf_value_validate`, `value_type_strict`, `namespace_info`, `version_keep_limit`, `version_keep_days`, `conf_name_order`, `description`, `created_at`, `updated_at`, `updated_by`) VALUES (75,'common','actconf','redis','act任务配置','redis相关配置','pub,app',NULL,0,1,0,NULL,0,0,0,'redis相关配置','2022-09-16 14:34:33','2023-03-22 12:08:50','');
INSERT INTO `tb_config_file_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_type_lc`, `conf_file_lc`, `level_names`, `level_versioned`, `conf_name_validate`, `conf_value_validate`, `value_type_strict`, `namespace_info`, `version_keep_limit`, `version_keep_days`, `conf_name_order`, `description`, `created_at`, `updated_at`, `updated_by`) VALUES (210,'common','backup_client','config.toml','','backup base config','plat,app','',1,1,1,'',0,0,0,'备份客户端','2023-03-09 17:40:06','2023-07-20 17:46:29','');
INSERT INTO `tb_config_file_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_type_lc`, `conf_file_lc`, `level_names`, `level_versioned`, `conf_name_validate`, `conf_value_validate`, `value_type_strict`, `namespace_info`, `version_keep_limit`, `version_keep_days`, `conf_name_order`, `description`, `created_at`, `updated_at`, `updated_by`) VALUES (212,'common','backup_client','cosinfo.toml','','backup auth config','plat,app','',1,1,1,'',0,0,0,'备份客户端','2023-03-09 17:40:06','2023-07-20 17:46:33','');
INSERT INTO `tb_config_file_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_type_lc`, `conf_file_lc`, `level_names`, `level_versioned`, `conf_name_validate`, `conf_value_validate`, `value_type_strict`, `namespace_info`, `version_keep_limit`, `version_keep_days`, `conf_name_order`, `description`, `created_at`, `updated_at`, `updated_by`) VALUES (73,'common','osconf','os','操作系统配置',NULL,'plat,app,cluster',NULL,0,1,0,NULL,0,0,0,NULL,'2022-09-02 17:05:43','2023-03-20 21:40:05','');
/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

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
-- Dumping data for table `tb_config_name_def`
--
-- WHERE:  namespace='common' AND (flag_encrypt!=1 or value_default like '{{%')

INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8872,'common','actconf','redis','delete_rate','INT','20000','[1,100000]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,NULL,'2022-09-16 12:01:44','2023-03-22 14:24:58',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8873,'common','actconf','redis','tendisplus_delete_rate','INT','3000','[1,100000]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,NULL,'2022-09-16 12:09:00','2023-03-22 14:25:06',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16750,'common','backup_client','config.toml','cfg.file_tag_allowed','STRING','REDIS_BINLOG,INCREMENT_BACKUP,REDIS_FULL,MYSQL_FULL_BACKUP,BINLOG,OSDATA,MONGO_INCR_BACKUP,LOG,ORACLE,OTHER','','',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:58',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16751,'common','backup_client','config.toml','cfg.net_addr','STRING','{{.NetAddr}}','','',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:53',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16747,'common','backup_client','config.toml','coslimit.block_size','INT','100','[0, 9999999]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:57',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16749,'common','backup_client','config.toml','coslimit.local_file_limit','INT','100','[0, 9999999]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:54',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16748,'common','backup_client','config.toml','coslimit.local_total_limit','INT','100','[0, 9999999]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:56',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16756,'common','backup_client','cosinfo.toml','app_attr.bk_biz_id','INT','{{.AppAttr.BkBizId}}','[0, 9999999]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:59',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16757,'common','backup_client','cosinfo.toml','app_attr.bk_cloud_id','INT','{{.AppAttr.BkCloudId}}','[0, 9999999]','RANGE',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:50:01',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16755,'common','backup_client','cosinfo.toml','cos_auth.bucket_name','STRING','{{.CosAuth.BucketName}}','','',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:47',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16752,'common','backup_client','cosinfo.toml','cos_auth.region','STRING','{{.CosAuth.Region}}','','',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:51',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16753,'common','backup_client','cosinfo.toml','cos_auth.secret_id','STRING','{{.CosAuth.SecretId}}','','',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:50',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16754,'common','backup_client','cosinfo.toml','cos_auth.secret_key','STRING','{{.CosAuth.SecretKey}}','','',1,0,0,0,0,NULL,NULL,NULL,-1,NULL,'If more than this many successive connection requests from a host are interrupted without a successful connection, the server blocks that host from further connections.','2022-04-25 10:00:47','2023-07-20 17:49:49',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8821,'common','osconf','os','user','STRING','mysql',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-09-02 17:21:18','2022-09-05 15:06:45',0);
/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

