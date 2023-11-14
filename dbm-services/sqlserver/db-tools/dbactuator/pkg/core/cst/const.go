/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cst

const (
	// Environment TODO
	Environment = "enviroment"
	// Test TODO
	Test = "test"
)

const (
	// TIMELAYOUT TODO
	TIMELAYOUT = "2006-01-02 15:04:05"
	// TIMELAYOUTSEQ TODO
	TIMELAYOUTSEQ = "2006-01-02_15:04:05"
	// TimeLayoutDir TODO
	TimeLayoutDir = "20060102150405"
)

const (
	// BASE_DATA_PATH 默认基础数据盘符,默认D盘
	BASE_DATA_PATH = "D:\\"
	// BASE_BACKUP_PATH 默认基础备份盘符，默认E盘
	BASE_BACKUP_PATH = "E:\\"
	// BK_PKG_INSTALL_NAME 默认可执行文件的目录名称
	BK_PKG_INSTALL_NAME = "install"
	// MSSQL_DATA_NAME 默认存储数据的目录名称
	MSSQL_DATA_NAME = "gamedb"
	// MSSQL_BACKUP_NAME 默认存储日志的目录名称
	MSSQL_BACKUP_NAME = "dbbak"
	// CONFIGURATION_FILE_NAME 实例安装文件名称
	CONFIGURATION_FILE_NAME = "configuationfile"
	// DB_PORT_INIT 默认DB起始端口
	DB_PORT_INIT = 48322
	// MIRRORING_PORT_INIT 镜像服务起始端口
	MIRRORING_PORT_INIT = 37022
	// INSTALL_SHARED_DIR TODO
	INSTALL_SHARED_DIR = "C:\\Program Files\\Microsoft SQL Server"
	// INSTALL_SHARED_WOW_DIR TODO
	INSTALL_SHARED_WOW_DIR = "C:\\Program Files (x86)\\Microsoft SQL Server"
	// INSTANCE_DIR TODO
	INSTANCE_DIR = "C:\\Program Files\\Microsoft SQL Server"
	// INSTALL_SQL_DATA_DIR TODO
	INSTALL_SQL_DATA_DIR = "D:\\Microsoft SQL Server"
	// IEOD_FILE_BACKUP 备份系统上传的必需目录
	IEOD_FILE_BACKUP = "IEOD_FILE_BACKUP"
	// SQLSERVER_UNZIP_TOOL TODO
	// SQLserver安装包解压工具，默认初始化会有7z解压工具
	SQLSERVER_UNZIP_TOOL = "C:\\Program Files\\7-Zip\\7z"
)

// 定义一些sqlserver专用的注册表信息
const (
	MASTER_KEY_SHORT = "HKLM:\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
	MASTER_KEY       = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Microsoft SQL Server\\"
	DETAIL_KEY       = "\\MSSQLServer\\SuperSocketNetLib\\Tcp"
	DETAIL_HADR_KEY  = "\\MSSQLServer"
)

// 定义不同mssql版本的sqlcmd的文件路径

const (
	// SQLCMD_2019 TODO
	SQLCMD_2019 = "C:\\Program Files\\Microsoft SQL Server\\Client SDK\\ODBC\170\\Tools\\Binn\\SQLCMD.EXE"
	// SQLCMD_2017 TODO
	SQLCMD_2017 = "C:\\Program Files\\Microsoft SQL Server\\Client SDK\\ODBC\150\\Tools\\Binn\\SQLCMD.EXE"
	// SQLCMD_2016 TODO
	SQLCMD_2016 = "C:\\Program Files\\Microsoft SQL Server\\Client SDK\\ODBC\130\\Tools\\Binn\\SQLCMD.EXE"
	// SQLCMD_2014 TODO
	SQLCMD_2014 = "C:\\Program Files\\Microsoft SQL Server\\Client SDK\\ODBC\110\\Tools\\Binn\\SQLCMD.EXE"
	// SQLCMD_2012 TODO
	SQLCMD_2012 = "C:\\Program Files\\Microsoft SQL Server\\110\\Tools\\Binn\\SQLCMD.EXE"
	// SQLCMD_2008 TODO
	SQLCMD_2008 = "C:\\Program Files\\Microsoft SQL Server\\100\\Tools\\Binn\\SQLCMD.EXE"
)

// 定义数据同步模式
const (
	MIRRORING = 1
	ALWAYSON  = 2
)

// 定义一些常用的检查SQL

const (
	// 查出业务数据库，过滤只读库,异常库 和系统库
	GET_BUSINESS_DATABASE = "select name from master.sys.databases " +
		"where is_read_only=0 and database_id>4 and name not in('monitor') " +
		"and state = 0"

	// 查看镜像库连接异常的情况
	CHECK_MIRRORING_ABNORMAL = "SELECT name from  master.sys.databases " +
		"where database_id in " +
		"(select database_id from master.sys.database_mirroring " +
		"where mirroring_guid is not null and mirroring_state<>4)"
	// 查看ALWAYSON异常的情况(没有副本)
	CHECK_ALWAYSON_NO_COPY = "select count(1) from sys.dm_hadr_availability_replica_states where is_local=0"
	// 查看ALWAYSON异常的情况（副本异常）
	CHECK_ALWAYSON_ABNORMAL = "select count(1) from sys.dm_hadr_availability_replica_states " +
		"where is_local=0 and connected_state=0"
	// 查看ALWAYSON情况下，数据库同步异常的情况
	CHECK_ALWAYSON_DB_ABNORMAL = "SELECT name from master.sys.databases " +
		"where database_id in(SELECT database_id from sys.dm_hadr_database_replica_states " +
		"where is_local=0 and synchronization_state<>1)"
	// 查看ALWAYSON情况下，数据库没有配置同步的情况
	CHECK_ALWAYSON_DB_NO_DEPLOY = "SELECT name from master.sys.databases " +
		" where state=0 and is_read_only=0 and  database_id>4 and name not in('monitor') " +
		" and database_id not in(SELECT database_id from sys.dm_hadr_database_replica_states " +
		"where is_local=0 and synchronization_state=1)"
	// 查看镜像库延时落后大于1GB的情况
	CHECK_MIRRORING_DB_DELAY = "SELECT instance_name FROM master.sys.dm_os_performance_counters " +
		"WHERE object_name LIKE '%Database Mirroring%' AND counter_name='Log Send Queue KB' " +
		"and instance_name !='_Total' and cntr_value>1048576"
	// 查看ALWAYSON延时落后大于1GB的情况
	CHECK_ALWAYSON_DB_DELAY = "SELECT name from master.sys.databases " +
		" where state=0 and is_read_only=0 " +
		" and database_id in(SELECT database_id from sys.dm_hadr_database_replica_states " +
		" where is_local=0 and secondary_lag_seconds>1048576)"
)

// 获取实例的login user 的相关信息

const (
	GET_LOGIN_INFO = "select a.name as login_name ,a.sid as sid, " +
		"password_hash,default_database_name,dbcreator,sysadmin, " +
		"securityadmin,serveradmin,setupadmin,processadmin,diskadmin,bulkadmin " +
		"from master.sys.sql_logins a left join sys.syslogins b " +
		"on a.name=b.name where principal_id>4 and a.name not in('monitor') and a.is_disabled = 0"
)
