alter table tb_accounts drop column `cluster_type`;
alter table tb_account_rules drop column `cluster_type`;
alter table tb_accounts drop index  idx_bk_biz_id_cluster_type_user, add unique key
    bk_biz_id (bk_biz_id,`user`);
alter table tb_account_rules drop index idx_bk_biz_id_cluster_type_account_id_dbname, add unique key
    bk_biz_id (bk_biz_id,account_id,dbname);
