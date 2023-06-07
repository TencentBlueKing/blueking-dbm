SET NAMES utf8;
alter table tb_accounts add column `cluster_type`
    varchar(64) NOT NULL COMMENT '账号规则适用的集群类型' after bk_biz_id;
alter table tb_account_rules add column `cluster_type`
    varchar(64) NOT NULL COMMENT '账号规则适用的集群类型' after bk_biz_id;
alter table tb_accounts drop index bk_biz_id, add unique key
    idx_bk_biz_id_cluster_type_user (bk_biz_id,cluster_type,`user`);
alter table tb_account_rules drop index bk_biz_id, add unique key
    idx_bk_biz_id_cluster_type_account_id_dbname (bk_biz_id,cluster_type,account_id,dbname);
