CREATE DATABASE if not exists test;
create table IF NOT EXISTS test.free_space(a int) engine = InnoDB;
CREATE TABLE if not exists test.conn_log(
    conn_id bigint default NULL,
    conn_time datetime default NULL,
    user_name varchar(128) default NULL,
    cur_user_name varchar(128) default NULL,
    ip varchar(15) default NULL,
    key conn_time(conn_time)
);
create database if not exists db_infobase;
create table if not exists db_infobase.checksum(
    db char(64) NOT NULL,
    tbl char(64) NOT NULL,
    chunk int(11) NOT NULL,
    boundaries text NOT NULL,
    this_crc char(40) NOT NULL,
    this_cnt int(11) NOT NULL,
    master_crc char(40) default NULL,
    master_cnt int(11) default NULL,
    ts timestamp NOT NULL,
    PRIMARY KEY (db, tbl, chunk)
);
replace into db_infobase.checksum values('test', 'test', 0, '1=1', '0', 0, '0', 0, now());
CREATE TABLE if not exists db_infobase.spes_status(
    ip varchar(15) default '',
    spes_id smallint default 0,
    report_day int default 0,
    PRIMARY KEY ip_id_day (ip, spes_id, report_day)
);
CREATE TABLE IF NOT EXISTS db_infobase.master_slave_check (
    check_item VARCHAR(64) NOT NULL PRIMARY KEY comment 'check_item to check',
    master VARCHAR(64) comment 'the check_item status on master',
    slave VARCHAR(64) comment 'the check_item status on slave',
    check_result VARCHAR(64) comment 'the different value of master and slave'
) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS db_infobase.check_heartbeat (
    uid INT NOT NULL PRIMARY KEY,
    ck_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP on  UPDATE CURRENT_TIMESTAMP
) ENGINE = InnoDB;
REPLACE INTO db_infobase.check_heartbeat(uid) value(1);
INSERT INTO db_infobase.master_slave_check
values('slave_delay_sec', now(), now(), 0);
CREATE TABLE IF NOT EXISTS db_infobase.query_response_time(
    time_min INT(11) NOT NULL DEFAULT '0',
    time VARCHAR(14) NOT NULL DEFAULT '',
    total VARCHAR(100) NOT NULL DEFAULT '',
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (time_min, time)
);
flush logs;