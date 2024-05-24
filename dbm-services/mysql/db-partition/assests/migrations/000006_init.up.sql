SET NAMES utf8;
alter table mysql_partition_cron_log drop column bk_biz_id,drop column cluster_id,drop column ticket_id,
    drop column immute_domain,drop column bk_cloud_id,drop column time_zone;
alter table spider_partition_cron_log drop column bk_biz_id,drop column cluster_id,drop column ticket_id,
    drop column immute_domain,drop column bk_cloud_id,drop column time_zone;
