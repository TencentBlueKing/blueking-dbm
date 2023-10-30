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
-- WHERE:  namespace='riak'

INSERT INTO `tb_config_file_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_type_lc`, `conf_file_lc`, `level_names`, `level_versioned`, `conf_name_validate`, `conf_value_validate`, `value_type_strict`, `namespace_info`, `version_keep_limit`, `version_keep_days`, `conf_name_order`, `description`, `created_at`, `updated_at`, `updated_by`) VALUES (208,'riak','dbconf','riak-22','riak-2.2','riak-2.2 config','plat,app,cluster','cluster',1,1,0,'Riak',5,365,0,NULL,'2023-03-30 19:17:40','2023-10-26 16:17:41','');
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
-- WHERE:  namespace='riak' AND (flag_encrypt!=1 or value_default like '{{%')

INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16498,'riak','dbconf','riak-22','bucket_types','STRING','player_preferences','player_preferences | ','ENUMS',2,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-04-25 10:00:47','2023-10-26 16:19:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16499,'riak','dbconf','riak-22','distributed_cookie','STRING','testriak','mixedriak | mhsriak | ppriak | testriak','ENUM',2,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-04-25 10:00:47','2023-10-26 16:19:39',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16494,'riak','dbconf','riak-22','leveldb_expiration','STRING','off','off | on','ENUM',2,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-04-25 10:00:47','2023-10-26 16:20:09',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16495,'riak','dbconf','riak-22','leveldb_expiration_mode','STRING','whole_file','whole_file','ENUM',2,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-04-25 10:00:47','2023-10-26 16:20:34',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16496,'riak','dbconf','riak-22','leveldb_expiration_retention_time','STRING','unlimited','unlimited | 365d','ENUM',2,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-04-25 10:00:47','2023-10-26 16:19:59',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (16497,'riak','dbconf','riak-22','ring_size','INT','256','[256,256]','RANGE',2,0,0,0,1,NULL,NULL,NULL,-1,NULL,NULL,'2022-04-25 10:00:47','2023-10-25 17:49:11',0);
/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

