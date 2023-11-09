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

const GET_LINKSERVERS_INFO = `
USE [master]

DECLARE @servername NVARCHAR(2000)
DECLARE @id INT 
DECLARE @scriptdate NVARCHAR(200)
DECLARE @productName NVARCHAR(2000) 
DECLARE @datasource NVARCHAR(4000) 
DECLARE @useself BIT  
DECLARE @dist BIT
DECLARE @remoteuser NVARCHAR(2000) 
DECLARE @collationcompatible BIT 
DECLARE @dataaccess BIT 
DECLARE @sub BIT
DECLARE @pub BIT 
DECLARE @rpc BIT 
DECLARE @rpcout BIT 
DECLARE @connecttimeout BIGINT 
DECLARE @lazyschemavalidation BIT 
DECLARE @querytimeout BIGINT 
DECLARE @useremotecollation BIT 
DECLARE @remoteproctransactionpromotion BIT
DECLARE @sql VARCHAR(max)
SET @sql=''
DECLARE LinkserverNameCur CURSOR
FOR
    SELECT srv.name AS [Name] ,
    CAST(srv.server_id AS INT) AS [ID]
    FROM sys.servers AS srv
    WHERE ( srv.server_id != 0 ) 

OPEN LinkserverNameCur
FETCH NEXT FROM LinkserverNameCur INTO @servername, @id
WHILE @@FETCH_STATUS = 0
    BEGIN
    SELECT @servername = srv.name ,
    @datasource = ISNULL(srv.data_source, N'''') ,
    @productName = srv.product ,
    @collationcompatible = CAST(srv.is_collation_compatible AS BIT) ,
    @dataaccess = CAST(srv.is_data_access_enabled AS BIT) ,
    @dist = CAST(srv.is_distributor AS BIT) ,
    @pub = CAST(srv.is_publisher AS BIT) ,
    @rpc = CAST(srv.is_remote_login_enabled AS BIT) ,
    @rpcout = CAST(srv.is_rpc_out_enabled AS BIT) ,
    @sub = CAST(srv.is_subscriber AS BIT) ,
    @connecttimeout = srv.connect_timeout ,
    @lazyschemavalidation = srv.lazy_schema_validation ,
    @querytimeout = srv.query_timeout ,
    @useremotecollation = srv.uses_remote_collation ,
    @remoteproctransactionpromotion = CAST(srv.is_remote_proc_transaction_promotion_enabled AS BIT)
    FROM sys.servers AS srv
    WHERE ( srv.server_id != 0 ) AND ( srv.name = @servername ) AND ( srv.[server_id] = @id )

 SELECT 
    @remoteuser = ISNULL(ll.remote_name, N'') ,
    @useself = CAST(ll.uses_self_credential AS BIT)
 FROM sys.servers AS srv
    INNER JOIN sys.linked_logins ll ON ll.server_id = CAST(srv.server_id AS INT)
    LEFT OUTER JOIN sys.server_principals sp ON ll.local_principal_id = sp.principal_id
 WHERE ( ( srv.server_id != 0 ) AND ( srv.name = @servername) AND ll.remote_name is null)

    IF (@servername IS NOT NULL AND @id IS NOT NULL)
    BEGIN 
    SELECT @scriptdate=CONVERT(NVARCHAR(200),GETDATE(),120)

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'USE [master]'
    
    SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF NOT EXISTS (SELECT srv.name FROM sys.servers srv WHERE srv.server_id != 0 AND srv.name = N'''+@servername+''')'
    
    SET @sql=@sql+CHAR(13)+CHAR(10) + 'BEGIN'
    
    IF @datasource like '%.%'
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_addlinkedserver @server = N'''+@servername+''', @srvproduct=N'''+@productName+''', @provider=N''SQLNCLI'', @datasrc=N'''+@datasource+''''
    ELSE
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_addlinkedserver @server = N'''+@servername+''', @srvproduct=N'''+@productName+''''
    
    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_addlinkedsrvlogin @rmtsrvname=N'''+@servername+''',@useself=N''True'',@locallogin=NULL,@rmtuser=NULL,@rmtpassword=NULL'
    
    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_addlinkedsrvlogin @rmtsrvname=N'''+@servername+''',@useself=N''True'',@locallogin=''sa'',@rmtuser=NULL,@rmtpassword=NULL'

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''collation compatible'', @optvalue=N'''+CASE @useself WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''data access'', @optvalue=N'''+CASE @dataaccess WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''dist'', @optvalue=N'''+CASE @dist WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''pub'', @optvalue=N'''+CASE @pub WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''rpc'', @optvalue=N'''+CASE @rpc WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''rpc out'', @optvalue=N'''+CASE @rpcout WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''sub'', @optvalue=N'''+CASE @sub WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''connect timeout'', @optvalue=N'''+CAST(@connecttimeout AS NVARCHAR(200))+''''

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''lazy schema validation'', @optvalue=N'''+CASE @lazyschemavalidation WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''query timeout'', @optvalue=N'''+CAST(@querytimeout AS NVARCHAR(200))+''''

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''use remote collation'', @optvalue=N'''+CASE @useremotecollation WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''remote proc transaction promotion'', @optvalue=N'''+CASE @remoteproctransactionpromotion WHEN 0 THEN 'false' ELSE 'true' END+'''' 

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'END'
    
    END 

    FETCH NEXT FROM LinkserverNameCur INTO @servername, @id
END
CLOSE LinkserverNameCur
DEALLOCATE LinkserverNameCur

SELECT @sql as linkserver_sql
`
