SET NAMES utf8;
alter table mysql_partition_config add index `idx_db_app_abbr_bk_biz_id` (`db_app_abbr`,`bk_biz_id`);
alter table spider_partition_config add index `idx_db_app_abbr_bk_biz_id` (`db_app_abbr`,`bk_biz_id`);
