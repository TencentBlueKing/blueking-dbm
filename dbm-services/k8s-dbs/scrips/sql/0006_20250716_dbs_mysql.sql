-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_cluster_config ADD COLUMN is_public tinyint(1) DEFAULT 1 COMMENT '是否公有集群,0:私有，1:公有' AFTER password;
ALTER TABLE tb_k8s_cluster_config ADD COLUMN region_name VARCHAR(32) COMMENT '区域名称' AFTER is_public;
ALTER TABLE tb_k8s_cluster_config ADD COLUMN region_code VARCHAR(32) COMMENT '区域编码' AFTER region_name;
ALTER TABLE tb_k8s_cluster_config ADD COLUMN provider VARCHAR(32) COMMENT '云服务提供商' AFTER region_code;

