USE bkbase_dbs;
SET NAMES utf8;

ALTER TABLE tb_k8s_crd_opsrequest ADD COLUMN completed_at timestamp NULL DEFAULT NULL  COMMENT '操作结束时间' AFTER status;