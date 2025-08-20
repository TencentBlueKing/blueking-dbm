CREATE TABLE `checksum`
(
    `master_ip`      char(32)  NOT NULL DEFAULT '0.0.0.0',
    `master_port`    int(11) NOT NULL DEFAULT '3306',
    `db`             char(64)  NOT NULL,
    `tbl`            char(64)  NOT NULL,
    `chunk`          int(11) NOT NULL,
    `chunk_time`     float              DEFAULT NULL,
    `chunk_index`    varchar(200)       DEFAULT NULL,
    `lower_boundary` blob,
    `upper_boundary` blob,
    `this_crc`       char(40)  NOT NULL,
    `this_cnt`       int(11) NOT NULL,
    `master_crc`     char(40)           DEFAULT NULL,
    `master_cnt`     int(11) DEFAULT NULL,
    `ts`             timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `ticket_id`      bigint(20) NOT NULL DEFAULT '0',
    PRIMARY KEY (`master_ip`, `master_port`, `db`, `tbl`, `chunk`, `ticket_id`),
    KEY              `db_tbl_chunk` (`db`,`tbl`,`chunk`),
    KEY              `ts_db_tbl` (`ts`,`db`,`tbl`),
    KEY              `ticket_id` (`ticket_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE TABLE `checksum_history`
(
    `master_ip`      char(32)  NOT NULL DEFAULT '0.0.0.0',
    `master_port`    int(11) NOT NULL DEFAULT '3306',
    `db`             char(64)  NOT NULL,
    `tbl`            char(64)  NOT NULL,
    `chunk`          int(11) NOT NULL,
    `chunk_time`     float              DEFAULT NULL,
    `chunk_index`    varchar(200)       DEFAULT NULL,
    `lower_boundary` blob,
    `upper_boundary` blob,
    `this_crc`       char(40)  NOT NULL,
    `this_cnt`       int(11) NOT NULL,
    `master_crc`     char(40)           DEFAULT NULL,
    `master_cnt`     int(11) DEFAULT NULL,
    `ts`             timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `ticket_id`      bigint(20) NOT NULL DEFAULT '0',
    `reported`       int(11) DEFAULT '0',
    PRIMARY KEY (`master_ip`, `master_port`, `db`, `tbl`, `chunk`, `ticket_id`, `ts`),
    KEY              `db_tbl_chunk` (`db`,`tbl`,`chunk`),
    KEY              `ts_db_tbl` (`ts`,`db`,`tbl`),
    KEY              `ticket_id` (`ticket_id`),
    KEY              `idx_reported` (`reported`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;