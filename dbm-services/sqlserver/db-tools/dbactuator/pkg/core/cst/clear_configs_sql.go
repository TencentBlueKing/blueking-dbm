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

var CLEAR_JOB_SQL = `
DECLARE @job_name NVARCHAR(128);
DECLARE job_cursor CURSOR FOR 
SELECT name FROM msdb.dbo.sysjobs
where name not like 'TC_%'
AND name not in('syspolicy_purge_history');

OPEN job_cursor;

FETCH NEXT FROM job_cursor INTO @job_name;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC msdb.dbo.sp_delete_job @job_name = @job_name, @delete_unused_schedule=1;
    FETCH NEXT FROM job_cursor INTO @job_name;
END;

CLOSE job_cursor;
DEALLOCATE job_cursor;
`

var CLEAR_LINKSERVER_SQL = `
DECLARE @linked_server_name SYSNAME;
DECLARE linked_server_cursor CURSOR FOR 
SELECT name FROM sys.servers WHERE is_linked = 1;

OPEN linked_server_cursor;

FETCH NEXT FROM linked_server_cursor INTO @linked_server_name;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC sp_dropserver @server=@linked_server_name, @droplogins='droplogins';
    FETCH NEXT FROM linked_server_cursor INTO @linked_server_name;
END;

CLOSE linked_server_cursor;
DEALLOCATE linked_server_cursor;
`
