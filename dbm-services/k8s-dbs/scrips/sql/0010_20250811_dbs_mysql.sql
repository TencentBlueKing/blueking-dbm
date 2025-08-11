-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_crd_cluster ADD COLUMN termination_policy varchar(32) COMMENT '集群删除策略' AFTER topo_name;