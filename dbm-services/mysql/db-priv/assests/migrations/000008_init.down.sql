SET NAMES utf8;
ALTER TABLE tb_accounts CONVERT TO CHARACTER SET utf8;
ALTER TABLE tb_account_rules CONVERT TO CHARACTER SET utf8;
ALTER TABLE tb_passwords CONVERT TO CHARACTER SET utf8;
ALTER TABLE tb_security_rules CONVERT TO CHARACTER SET utf8;
ALTER TABLE priv_logs drop index idx_execute_time;
ALTER TABLE priv_logs drop index idx_bk_biz_id_ticket_execute_time;
ALTER TABLE priv_logs drop primary key, add primary key (id);
