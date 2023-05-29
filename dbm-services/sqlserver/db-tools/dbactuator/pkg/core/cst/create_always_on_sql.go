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

var CREATE_AlWAYS_ON_IN_DB = `
DECLARE @group_name VARCHAR(100),@SQL VARCHAR(1000)

IF '%s'='all' AND EXISTS(SELECT 1 FROM master.sys.dm_hadr_availability_replica_states where is_local=1)
BEGIN
	SELECT @group_name=name from sys.availability_groups
	SET @SQL='DROP AVAILABILITY GROUP ['+@group_name+']'
	EXEC(@SQL)
END

USE [master]

IF NOT EXISTS(SELECT 1 FROM sys.availability_groups)
BEGIN
	CREATE AVAILABILITY GROUP [%s]
	WITH (AUTOMATED_BACKUP_PREFERENCE = PRIMARY,
	DB_FAILOVER = OFF,
	DTC_SUPPORT = NONE,
	CLUSTER_TYPE = NONE,
	REQUIRED_SYNCHRONIZED_SECONDARIES_TO_COMMIT = 0)
	FOR 
	REPLICA ON N'%s' WITH (
		ENDPOINT_URL = N'TCP://%s:%d',
		FAILOVER_MODE = MANUAL, 
		AVAILABILITY_MODE = ASYNCHRONOUS_COMMIT, 
		SESSION_TIMEOUT = 10, 
		BACKUP_PRIORITY = 50, 
		SEEDING_MODE = MANUAL, 
		PRIMARY_ROLE(ALLOW_CONNECTIONS = ALL), 
		SECONDARY_ROLE(ALLOW_CONNECTIONS = NO)
		);
END


IF NOT EXISTS(SELECT 1 FROM sys.availability_replicas where replica_server_name='%s')
BEGIN
	ALTER AVAILABILITY GROUP [%s] ADD REPLICA ON '%s'   
	WITH (ENDPOINT_URL = 'TCP://%s:%d',
	FAILOVER_MODE = MANUAL, 
	AVAILABILITY_MODE = ASYNCHRONOUS_COMMIT, 
	SESSION_TIMEOUT = 10, 
	BACKUP_PRIORITY = 50, 
	SEEDING_MODE = MANUAL, 
	PRIMARY_ROLE(ALLOW_CONNECTIONS = ALL), 
	SECONDARY_ROLE(ALLOW_CONNECTIONS = ALL)
	);
END
`

var CREATE_AlWAYS_ON_IN_DR = `
DECLARE @group_name VARCHAR(100),@SQL VARCHAR(1000)

IF EXISTS(SELECT 1 FROM master.sys.dm_hadr_availability_replica_states where is_local=1)
BEGIN
	SELECT @group_name=name from sys.availability_groups
	SET @SQL='DROP AVAILABILITY GROUP ['+@group_name+']'
	EXEC(@SQL)
END

USE [master]

IF NOT EXISTS(SELECT 1 FROM sys.availability_groups)
BEGIN
	ALTER AVAILABILITY GROUP [%s] JOIN WITH (CLUSTER_TYPE = NONE);
END
`

var ADD_DATABASE_IN_ALWAYS_ON_WITH_DB = `
USE [master]

DECLARE @server_group_name varchar(100),@SQL varchar(max)
SET @server_group_name=''

IF EXISTS(SELECT 1 FROM sys.availability_groups)
BEGIN 
	SELECT @server_group_name=name FROM sys.availability_groups

	SET @SQL = ''
	SELECT @SQL = ISNULL(@SQL+'','')+'ALTER AVAILABILITY GROUP ['+@server_group_name+'] ADD DATABASE ['+name+'];'
	from master.sys.databases 
	where database_id>4 
	and name not in('monitor') 
	and name in (%s)
	and replica_id is null  
	and recovery_model=1 
	and is_read_only=0 
	and state=0 
	and name NOT IN(SELECT NAME FROM MONITOR.DBO.MIRRORING_FILTER(NOLOCK)) 
	EXEC(@SQL)
END

`

var ADD_DATABASE_IN_ALWAYS_ON_WITH_DR = `
USE [master]
DECLARE @server_group_name varchar(100),@SQL varchar(max)
SET @server_group_name=''

IF EXISTS(SELECT 1 FROM sys.availability_groups)
BEGIN 
	SELECT @server_group_name=name FROM sys.availability_groups

	SET @SQL = ''
	SELECT @SQL = ISNULL(@SQL+'','')+'ALTER DATABASE ['+name+'] SET HADR AVAILABILITY GROUP = ['+@server_group_name+'];'
	from master.sys.databases 
	where database_id>4 
	and name not in('monitor') 
	and name in(%s) 
	and replica_id is null 
	and state=1 
	and recovery_model=1
	EXEC(@SQL)
END
`
