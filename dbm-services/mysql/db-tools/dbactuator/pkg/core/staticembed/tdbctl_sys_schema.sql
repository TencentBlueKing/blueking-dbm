

CREATE TABLE if not exists infodba_schema.cluster_schema_checksum(
    `db` char(64) NOT NULL,
    `tbl` char(64) NOT NULL,
    `status` char(32) NOT NULL DEFAULT "" COMMENT "检查结果,一致:ok,不一致:inconsistent",
    `checksum_result` json COMMENT "差异表结构信息,tdbctl checksum table 的结果",
    `update_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`db`,`tbl`),
);
-- example  
-- replace to  cluster_schema_checksum  values('db1','tb1','inconsistent','[{"Server_name":"SPT0","Db":"db1","Table":"t1","Status":"Error","Message":"(1)inconsistent field count, got 3, should be 2"}]',now());