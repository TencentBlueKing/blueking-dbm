CREATE TABLE IF NOT EXISTS binlog_rotate (
    bk_biz_id integer not null,
    cluster_id integer not null,
    cluster_domain varchar(120) default '',
    db_role varchar(20) not null default '',
    host varchar(64) not null,
    port integer default 0,
    filename varchar(64) not null,
    filesize integer not null,
    file_mtime varchar(32) not null,
    start_time varchar(32) default '',
    stop_time varchar(32) default '',
    backup_status integer default -2,
    backup_status_info varchar(120) not null default '',
    backup_taskid varchar(64) default '',
    created_at varchar(32) default '',
    updated_at varchar(32) default '',
    PRIMARY KEY(cluster_id,filename,host,port)
);

CREATE INDEX idx_status
    ON binlog_rotate (backup_status);