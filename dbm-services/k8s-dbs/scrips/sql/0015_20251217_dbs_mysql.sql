-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_cluster_config ADD COLUMN cluster_alias VARCHAR(32) COMMENT 'k8s 集群名称' AFTER cluster_name;