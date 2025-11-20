-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

CREATE UNIQUE INDEX unique_cluster_idx ON tb_k8s_crd_cluster (k8s_cluster_config_id, namespace, cluster_name);