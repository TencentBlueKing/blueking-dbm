CREATE TABLE IF NOT EXISTS time_interval (
    task_name varchar(64) not null,
    tag varchar(128) not null default '',
    last_run_at varchar(32) default '',
    PRIMARY KEY(task_name,tag)
);