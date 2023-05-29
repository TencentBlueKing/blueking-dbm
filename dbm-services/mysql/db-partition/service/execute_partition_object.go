package service

import (
	"time"
)

// PartitionConfig TODO
type PartitionConfig struct {
	ID                    int       `json:"id" gorm:"column:id;primary_key;auto_increment"`
	BkBizId               int       `json:"bk_biz_id" gorm:"column:bk_biz_id"`
	ImmuteDomain          string    `json:"immute_domain" gorm:"column:immute_domain"`
	Port                  int       `json:"port" gorm:"column:port"`
	BkCloudId             int       `json:"bk_cloud_id" gorm:"column:bk_cloud_id"`
	ClusterId             int       `json:"cluster_id" gorm:"column:cluster_id"`
	DbLike                string    `json:"dblike" gorm:"column:dblike"`
	TbLike                string    `json:"tblike" gorm:"column:tblike"`
	PartitionColumn       string    `json:"partition_columns" gorm:"column:partition_column"`
	PartitionColumnType   string    `json:"partition_column_type" gorm:"column:partition_column_type"`
	ReservedPartition     int       `json:"reserved_partition" gorm:"column:reserved_partition"`
	ExtraPartition        int       `json:"extra_partition" gorm:"column:extra_partition"`
	PartitionTimeInterval int       `json:"partition_time_interval" gorm:"column:partition_time_interval"`
	PartitionType         int       `json:"partition_type" gorm:"column:partition_type"`
	ExpireTime            int       `json:"expire_time"`
	Phase                 string    `json:"phase" gorm:"column:phase"`
	Creator               string    `json:"creator" gorm:"column:creator"`
	Updator               string    `json:"updator" gorm:"column:updator"`
	CreateTime            time.Time `json:"create_time" gorm:"column:create_time"`
	UpdateTime            time.Time `json:"update_time" gorm:"column:update_time"`
}

// PartitionConfigWithLog TODO
type PartitionConfigWithLog struct {
	PartitionConfig
	ExecuteTime  time.Time `json:"execute_time" gorm:"execute_time"`
	TicketId     int       `json:"ticket_id" gorm:"ticket_id"`
	Status       string    `json:"status" gorm:"status"`
	TicketStatus string    `json:"ticket_status" gorm:"ticket_status"`
	CheckInfo    string    `json:"check_info" gorm:"check_info"`
}

// ConfigDetail TODO
type ConfigDetail struct {
	PartitionConfig
	DbName      string `json:"dbname"`
	TbName      string `json:"tbname"`
	Partitioned bool   `json:"partitioned"`
}

// Ticket TODO
type Ticket struct {
	BkBizId    int    `json:"bk_biz_id"`
	TicketType string `json:"ticket_type"`
	Remark     string `json:"remark"`
	Details    Detail `json:"details"`
}

// Details TODO
type Details struct {
	Infos    []Info           `json:"infos"`
	Clusters ClustersResponse `json:"clusters"`
}

// ClustersResponse TODO
type ClustersResponse struct {
	ClusterResponse map[string]ClusterResponse `json:"cluster_response"`
}

// ClusterResponse TODO
type ClusterResponse struct {
	Id              int    `json:"id"`
	Creator         string `json:"creator"`
	Updater         string `json:"updater"`
	Name            string `json:"name"`
	Alias           string `json:"alias"`
	BkBizId         int    `json:"bk_biz_id"`
	ClusterType     string `json:"cluster_type"`
	DbModuleId      int    `json:"db_module_id"`
	ImmuteDomain    string `json:"immute_domain"`
	MajorVersion    string `json:"major_version"`
	Phase           string `json:"phase"`
	Status          string `json:"status"`
	BkCloudId       int    `json:"bk_cloud_id"`
	Region          string `json:"region"`
	TimeZone        string `json:"time_zone"`
	ClusterTypeName string `json:"cluster_type_name"`
}

// Detail TODO
type Detail struct {
	Infos []Info `json:"infos"`
}

// Info TODO
type Info struct {
	ConfigId         int               `json:"config_id"`
	ClusterId        int               `json:"cluster_id"`
	ImmuteDomain     string            `json:"immute_domain"`
	BkCloudId        int               `json:"bk_cloud_id"`
	PartitionObjects []PartitionObject `json:"partition_objects"`
}

// PartitionObject TODO
type PartitionObject struct {
	Ip             string         `json:"ip"`
	Port           int            `json:"port"`
	ShardName      string         `json:"shard_name"`
	ExecuteObjects []PartitionSql `json:"execute_objects"`
}

// ExecResult TODO
type ExecResult struct {
	IsSuccess bool
	Sql       string
	Msg       string
}

// Result TODO
type Result struct {
	ExecResult
	DbName string
	Action string
}

/*
show create table mysql_partition_conf\G
*************************** 1. row ***************************
       Table: mysql_partition_conf
Create Table: CREATE TABLE `mysql_partition_conf` (
  `ID` bigint(20) NOT NULL AUTO_INCREMENT,
  `App` varchar(100) NOT NULL,
  `Module` varchar(100) NOT NULL,
  `Ip` varchar(100) NOT NULL,
  `Port` int(11) NOT NULL,
  `DbLike` varchar(100) NOT NULL,
  `PartitionTableName` varchar(100) NOT NULL,
  `PartitionColumn` varchar(100) DEFAULT NULL,
  `PartitionColumnType` varchar(100) DEFAULT NULL,
  `ReservedPartition` int(11) NOT NULL,
  `ExtraPartition` int(11) NOT NULL,
  `PartitionTimeInterval` int(11) NOT NULL,
  `PartitionTimeWay` enum('DAY','MONTH') DEFAULT NULL,
  `PartitionType` int(11) NOT NULL,
  `IsExchange` int(11) NOT NULL DEFAULT '0',
  `HeartBeat` datetime NOT NULL DEFAULT '2000-01-01 00:00:00',
  `Alive` int(11) NOT NULL DEFAULT '3' COMMENT '1:success,2:failed,3:not execute,4+:others',
  `DoSuccess` int(11) DEFAULT NULL,
  `DoFailed` int(11) DEFAULT NULL,
  `Creator` varchar(100) DEFAULT NULL,
  `Updator` varchar(100) DEFAULT NULL,
  `CreateTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `UpdateTime` timestamp NOT NULL DEFAULT '2000-01-01 00:00:00',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `UK_MPT` (`App`,`Module`,`Ip`,`Port`,`DbLike`,`PartitionTableName`),
  UNIQUE KEY `uk_IPDT` (`Ip`,`Port`,`DbLike`,`PartitionTableName`),
  KEY `idx_app_alive` (`App`,`Alive`),
  KEY `IDX_DT` (`DbLike`,`PartitionTableName`),
  KEY `IDX_IDT` (`Ip`,`DbLike`,`PartitionTableName`)
) ENGINE=InnoDB AUTO_INCREMENT=74533 DEFAULT CHARSET=utf8mb4
1 row in set (0.00 sec)

select * from mysql_partition_conf limit 1\G
*************************** 1. row ***************************
                   ID: 25
                  App: web
               Module: web
                   Ip: gamedb.amspoint16.web.db
                 Port: 10000
               DbLike: dbcaccts
   PartitionTableName: t_acct_water_0
      PartitionColumn: Fcreate_time
  PartitionColumnType: timestamp
    ReservedPartition: 30
       ExtraPartition: 14
PartitionTimeInterval: 1
     PartitionTimeWay: DAY
        PartitionType: 5
           IsExchange: 0
            HeartBeat: 2023-02-12 01:30:08
                Alive: 1
            DoSuccess: 2
             DoFailed: 0
              Creator: NULL
              Updator: NULL
           CreateTime: 0000-00-00 00:00:00
           UpdateTime: 2000-01-01 00:00:00
1 row in set (0.00 sec)
*/
