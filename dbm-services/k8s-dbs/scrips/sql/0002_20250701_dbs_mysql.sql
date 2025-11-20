-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_biz_id int(11) COMMENT '业务的 cmdb id' AFTER `namespace`;
ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_biz_name varchar(128) COMMENT '业务名称' AFTER `bk_biz_id`;
ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_app_abbr VARCHAR(128) COMMENT '业务名称缩写' AFTER bk_biz_id;
ALTER TABLE tb_k8s_crd_cluster ADD COLUMN bk_app_code VARCHAR(128) COMMENT '蓝鲸 app 名称' AFTER bk_app_abbr;
ALTER TABLE tb_k8s_crd_cluster ADD COLUMN cluster_alias varchar(32) COMMENT '集群别名' AFTER `cluster_name`;