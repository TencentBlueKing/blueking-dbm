SET NAMES utf8;
alter table mysql_partition_cron_log add index idx_status_create_time(status,create_time);
alter table spider_partition_cron_log add index idx_status_create_time(status,create_time);
