SET NAMES utf8;
alter table priv_logs add column ticket varchar(800) DEFAULT NULL COMMENT '单据' after bk_biz_id;
