-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_crd_cluster ADD COLUMN service_version varchar(32) COMMENT '引擎具体版本' AFTER addoncluster_version;