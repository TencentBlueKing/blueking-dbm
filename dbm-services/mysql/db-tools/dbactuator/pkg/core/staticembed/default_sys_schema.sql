SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;
set binlog_format=statement;
CREATE DATABASE if not exists test;
CREATE DATABASE IF NOT EXISTS `infodba_schema` DEFAULT CHARACTER SET utf8;
create table IF NOT EXISTS infodba_schema.free_space(a int) engine = InnoDB;
CREATE TABLE if not exists infodba_schema.conn_log(
    conn_id bigint default NULL,
    conn_time datetime default NULL,
    user_name varchar(128) default NULL,
    cur_user_name varchar(128) default NULL,
    ip varchar(15) default NULL,
    key conn_time(conn_time)
) engine = InnoDB;

create table if not exists infodba_schema.`checksum`(
    master_ip char(32) NOT NULL DEFAULT '0.0.0.0',
    master_port int(11) NOT NULL DEFAULT '3306',
    db char(64) NOT NULL,
    tbl char(64) NOT NULL,
    chunk int(11) NOT NULL,
    chunk_time float DEFAULT NULL,
    chunk_index varchar(200) DEFAULT NULL,
    lower_boundary blob,
    upper_boundary blob,
    this_crc char(40) NOT NULL,
    this_cnt int(11) NOT NULL,
    master_crc char(40) DEFAULT NULL,
    master_cnt int(11) DEFAULT NULL,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`master_ip`,`master_port`,`db`,`tbl`,`chunk`),
    KEY `ts_db_tbl` (`ts`,`db`,`tbl`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
replace into infodba_schema.checksum
values('0.0.0.0','3306', 'test', 'test', 0, NULL, NULL, '1=1', '1=1', '0', 0, '0', 0, now());

CREATE TABLE if not exists infodba_schema.`checksum_history` (
   `master_ip` char(32) NOT NULL DEFAULT '0.0.0.0',
   `master_port` int(11) NOT NULL DEFAULT '3306',
   `db` char(64) NOT NULL,
   `tbl` char(64) NOT NULL,
   `chunk` int(11) NOT NULL,
   `chunk_time` float DEFAULT NULL,
   `chunk_index` varchar(200) DEFAULT NULL,
   `lower_boundary` blob,
   `upper_boundary` blob,
   `this_crc` char(40) NOT NULL,
   `this_cnt` int(11) NOT NULL,
   `master_crc` char(40) DEFAULT NULL,
   `master_cnt` int(11) DEFAULT NULL,
   `ts` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
   `reported` int(11) DEFAULT '0',
   PRIMARY KEY (`master_ip`,`master_port`,`db`,`tbl`,`chunk`,`ts`),
   KEY `ts_db_tbl` (`ts`,`db`,`tbl`),
   KEY `idx_reported` (`reported`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE if not exists infodba_schema.spes_status(
    ip varchar(15) default '',
    spes_id smallint default 0,
    report_day int default 0,
    PRIMARY KEY ip_id_day (ip, spes_id, report_day)
) engine = InnoDB;
CREATE TABLE IF NOT EXISTS infodba_schema.check_heartbeat (
    uid INT UNSIGNED  NOT NULL PRIMARY KEY,
    ck_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP on  UPDATE CURRENT_TIMESTAMP
) ENGINE = InnoDB;
REPLACE INTO infodba_schema.check_heartbeat(uid) value(@@server_id);
CREATE TABLE IF NOT EXISTS infodba_schema.query_response_time(
    time_min INT(11) NOT NULL DEFAULT '0',
    time VARCHAR(14) NOT NULL DEFAULT '',
    total VARCHAR(100) NOT NULL DEFAULT '',
    update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (time_min, time)
) engine = InnoDB;
-- conn_log 所有用户可写. 注会导致所有用户可以看见 infodba_schema
REPLACE into `mysql`.`db`(`Host`,`Db`,`User`,`Select_priv`,`Insert_priv`, `Update_priv`,`Delete_priv`,`Create_priv`,`Drop_priv`)
 values('%','infodba_schema','','Y','Y',  'N','N','N','N');

flush privileges;
flush logs;