SET NAMES utf8;
alter table tb_passwords add column `bk_biz_id` int(11) DEFAULT NULL COMMENT '业务的 cmdb id' after component;
