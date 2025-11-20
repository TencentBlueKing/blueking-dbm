-- Create a database and set character set and collation

USE bkbase_dbs;
SET NAMES utf8;

CREATE UNIQUE INDEX unique_addon_idx ON tb_k8s_crd_storageaddon (addon_type, addon_version);