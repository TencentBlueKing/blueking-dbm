set names utf8;
ALTER TABLE mysql_partition_config ADD COLUMN db_app_abbr VARCHAR(128) NOT NULL COMMENT "业务名称缩写" AFTER bk_biz_id;
ALTER TABLE mysql_partition_config ADD COLUMN bk_biz_name VARCHAR(128) NOT NULL COMMENT "业务名称" AFTER db_app_abbr;

ALTER TABLE spider_partition_config ADD COLUMN db_app_abbr VARCHAR(128) NOT NULL COMMENT "业务名称缩写" AFTER bk_biz_id;
ALTER TABLE spider_partition_config ADD COLUMN bk_biz_name VARCHAR(128) NOT NULL COMMENT "业务名称写" AFTER db_app_abbr;
