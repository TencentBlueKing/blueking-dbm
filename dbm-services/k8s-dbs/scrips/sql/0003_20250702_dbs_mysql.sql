-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_crd_cluster ADD COLUMN topo_name varchar(32) COMMENT '集群拓扑' AFTER addoncluster_version;