SET NAMES utf8;
alter table tb_passwords modify column lock_until timestamp NULL DEFAULT NULL;

