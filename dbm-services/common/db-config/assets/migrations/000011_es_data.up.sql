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
-- WHERE:  namespace='es'

INSERT INTO `tb_config_file_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_type_lc`, `conf_file_lc`, `level_names`, `level_versioned`, `conf_name_validate`, `conf_value_validate`, `value_type_strict`, `namespace_info`, `version_keep_limit`, `version_keep_days`, `conf_name_order`, `description`, `created_at`, `updated_at`, `updated_by`) VALUES (74,'es','dbconf','7.10.2','elasticsearch.yml配置','ES-7.10','plat,app,cluster','cluster',1,1,0,NULL,5,365,0,'es配置文件','2022-09-05 17:00:13','2023-06-30 17:27:03','');
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
-- WHERE:  namespace='es' AND (flag_encrypt!=1 or value_default like '{{%')

INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8840,'es','dbconf','7.10.2','bootstrap.memory_lock','STRING','true','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8841,'es','dbconf','7.10.2','bootstrap.system_call_filter','STRING','false','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8843,'es','dbconf','7.10.2','cluster.initial_master_nodes','STRING','{{master_nodename}}',NULL,'',2,0,0,0,1,'{{master_nodename}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8826,'es','dbconf','7.10.2','cluster.name','STRING','{{cluster_name}}',NULL,'',2,0,0,0,1,'{{cluster_name}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 17:24:58','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8850,'es','dbconf','7.10.2','cluster.routing.allocation.same_shard.host','STRING','true','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:42','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8842,'es','dbconf','7.10.2','discovery.seed_hosts','STRING','{{master_ip}}',NULL,'',2,0,0,0,1,'{{master_ip}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8849,'es','dbconf','7.10.2','http.max_content_length','STRING','2048mb',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8836,'es','dbconf','7.10.2','http.port','INT','9200',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8845,'es','dbconf','7.10.2','indices.recovery.max_bytes_per_sec','STRING','200mb',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8830,'es','dbconf','7.10.2','network.host','STRING','{{host}}',NULL,'',2,0,0,0,1,'{{host}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8831,'es','dbconf','7.10.2','network.publish_host','STRING','{{host}}',NULL,'',2,0,0,0,1,'{{host}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8829,'es','dbconf','7.10.2','node.attr.rack_id','INT','1',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8828,'es','dbconf','7.10.2','node.attr.tag','STRING','hot','hot | cold','ENUM',1,0,0,0,1,'hot',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8832,'es','dbconf','7.10.2','node.data','STRING','{{isdata}}',NULL,'',2,0,0,0,1,'{{isdata}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8833,'es','dbconf','7.10.2','node.ingest','STRING','true','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8834,'es','dbconf','7.10.2','node.master','STRING','{{ismaster}}',NULL,'',2,0,0,0,1,'{{ismaster}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8835,'es','dbconf','7.10.2','node.ml','STRING','true','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8827,'es','dbconf','7.10.2','node.name','STRING','{{node_name}}',NULL,'',2,0,0,0,1,'{{node_name}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:31','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (12412,'es','dbconf','7.10.2','password','STRING','{{password}}',NULL,'',0,0,0,1,1,'{{password}}',NULL,NULL,-1,NULL,'es配置','2022-10-25 10:21:35','2023-03-22 18:11:33',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (15921,'es','dbconf','7.10.2','path_data','STRING','/data/esdata','NULL','',1,0,0,0,1,'NULL','NULL','NULL',-1,'NULL','数据路径','2023-03-30 08:33:44','2023-03-30 08:33:44',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (15922,'es','dbconf','7.10.2','path_log','STRING','/data/eslog','NULL','',1,0,0,0,1,'NULL','NULL','NULL',-1,'NULL','日志路径','2023-03-30 08:35:33','2023-03-30 08:35:33',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8844,'es','dbconf','7.10.2','processors','STRING','{{processors}}',NULL,'',2,0,0,0,1,'{{processors}}',NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2023-04-17 17:10:41',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8846,'es','dbconf','7.10.2','search.default_search_timeout','STRING','60s',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (12414,'es','dbconf','7.10.2','superpassword','STRING','{{superpassword}}',NULL,'',0,0,0,1,1,'{{superpassword}}',NULL,NULL,-1,NULL,'es配置','2022-10-25 10:23:49','2023-03-22 18:11:36',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (12415,'es','dbconf','7.10.2','superuser','STRING','{{superuser}}',NULL,'',0,0,0,0,1,'{{superuser}}',NULL,NULL,-1,NULL,'es配置','2022-10-25 10:23:49','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8847,'es','dbconf','7.10.2','thread_pool.write.queue_size','STRING','1000',NULL,'',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (12413,'es','dbconf','7.10.2','username','STRING','{{username}}',NULL,'',0,0,0,0,1,'{{username}}',NULL,NULL,-1,NULL,'es配置','2022-10-25 10:21:35','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8848,'es','dbconf','7.10.2','xpack.monitoring.collection.enabled','STRING','false','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
INSERT INTO `tb_config_name_def` (`id`, `namespace`, `conf_type`, `conf_file`, `conf_name`, `value_type`, `value_default`, `value_allowed`, `value_type_sub`, `flag_status`, `flag_disable`, `flag_locked`, `flag_encrypt`, `need_restart`, `value_formula`, `extra_info`, `conf_name_lc`, `order_index`, `since_version`, `description`, `created_at`, `updated_at`, `stage`) VALUES (8839,'es','dbconf','7.10.2','xpack.security.enabled','STRING','false','true | false','ENUM',1,0,0,0,1,NULL,NULL,NULL,-1,NULL,'es配置','2022-09-05 21:31:41','2022-11-18 11:30:10',0);
/*!50112 SET @disable_bulk_load = IF (@is_rocksdb_supported, 'SET SESSION rocksdb_bulk_load = @old_rocksdb_bulk_load', 'SET @dummy_rocksdb_bulk_load = 0') */;
/*!50112 PREPARE s FROM @disable_bulk_load */;
/*!50112 EXECUTE s */;
/*!50112 DEALLOCATE PREPARE s */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

