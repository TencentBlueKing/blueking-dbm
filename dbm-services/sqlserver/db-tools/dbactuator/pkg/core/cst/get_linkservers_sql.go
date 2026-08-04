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

// GET_LINKSERVERS_META retrieves per-linkedserver auth meta for the Go layer to decide
// how to assemble sp_addlinkedsrvlogin (useself vs remote credential).
// One row per linked server. Only the "default mapping" (locallogin = NULL) is considered
// for cloning; per-local-login overrides are intentionally NOT cloned.
const GET_LINKSERVERS_META = `
USE [master]
SELECT
    srv.name                                       AS name,
    CAST(ISNULL(ll.uses_self_credential, 1) AS BIT) AS useself,
    ISNULL(ll.remote_name, N'')                    AS remote_user
FROM sys.servers AS srv
LEFT OUTER JOIN sys.linked_logins AS ll
    ON ll.server_id = srv.server_id
   AND ll.local_principal_id = 0   -- default mapping: applies to all locallogins
WHERE srv.server_id != 0
  AND srv.is_linked = 1            -- exclude legacy remote servers (sp_addserver)
ORDER BY srv.name
`

// GET_LINKSERVERS_INFO generates the skeleton clone SQL for each linked server.
// NOTE: sp_addlinkedsrvlogin is intentionally NOT emitted here — the Go layer
// will assemble the correct login statement using GET_LINKSERVERS_META and the
// (optionally provided) encrypted remote credentials.
//
// DESIGN — "aggressive overwrite" is intentional:
// The generated skeleton starts with `sp_dropserver @droplogins='droplogins'`,
// which drops the target-side linked server AND every sp_addlinkedsrvlogin
// mapping attached to it (including per-user mappings a DBA may have added
// manually on the target). This is BY DESIGN because CloneLinkservers is meant
// for INTRA-CLUSTER node synchronization (primary/secondary, multi-replica):
// all nodes in a cluster MUST share identical linked-server configuration, so
// any extra per-user mapping on the target is treated as configuration drift
// and gets normalized away. If future use cases require preserving target-side
// customizations, add an explicit opt-in (e.g. a `preserve_target_logins` flag)
// rather than removing `@droplogins='droplogins'` here.
const GET_LINKSERVERS_INFO = `
USE [master]

DECLARE @servername NVARCHAR(2000)
DECLARE @id INT 
DECLARE @scriptdate NVARCHAR(200)
DECLARE @productName NVARCHAR(2000) 
DECLARE @provider NVARCHAR(2000)
DECLARE @datasource NVARCHAR(4000) 
DECLARE @dist BIT
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
DECLARE @catalog NVARCHAR(2000)
DECLARE @sql NVARCHAR(max)

-- one row per linked server; Go layer iterates and assembles login stmt per row
IF OBJECT_ID('tempdb..#linkserver_out') IS NOT NULL DROP TABLE #linkserver_out
CREATE TABLE #linkserver_out (name NVARCHAR(2000), linkserver_sql NVARCHAR(MAX))

DECLARE LinkserverNameCur CURSOR
FOR
    SELECT srv.name AS [Name] ,
    CAST(srv.server_id AS INT) AS [ID]
    FROM sys.servers AS srv
    WHERE ( srv.server_id != 0 ) AND ( srv.is_linked = 1 )

OPEN LinkserverNameCur
FETCH NEXT FROM LinkserverNameCur INTO @servername, @id
WHILE @@FETCH_STATUS = 0
    BEGIN
    -- reset @sql at every iteration so each row contains ONLY its own server's SQL
    SET @sql = ''

    SELECT @servername = srv.name ,
    @datasource = ISNULL(srv.data_source, N'''') ,
    @productName = ISNULL(srv.product, N'''') ,
    @provider = ISNULL(srv.provider, N'SQLNCLI') ,
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
    @remoteproctransactionpromotion = CAST(srv.is_remote_proc_transaction_promotion_enabled AS BIT) ,
    @catalog = ISNULL(srv.catalog, N'''')
    FROM sys.servers AS srv
    WHERE ( srv.server_id != 0 ) AND ( srv.name = @servername ) AND ( srv.[server_id] = @id )

    IF (@servername IS NOT NULL AND @id IS NOT NULL)
    BEGIN 
    SELECT @scriptdate=CONVERT(NVARCHAR(200),GETDATE(),120)

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'USE [master]'
    
    SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF EXISTS (SELECT srv.name FROM sys.servers srv WHERE srv.server_id != 0 AND srv.name = N'''+@servername+''')'

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'BEGIN'

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_dropserver @server=N'''+@servername+''', @droplogins=''droplogins'''

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'END'
    
    SET @sql=@sql+CHAR(13)+CHAR(10) + 'BEGIN'
    
    IF LEN(@datasource) > 0
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_addlinkedserver @server = N'''+@servername+''', @srvproduct=N'''+@productName+''', @provider=N'''+@provider+''', @datasrc=N'''+@datasource+''''+CASE WHEN @catalog IS NOT NULL AND @catalog <> N'''' THEN ', @catalog=N'''+@catalog+'''' ELSE '''' END
    ELSE
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_addlinkedserver @server = N'''+@servername+''', @srvproduct=N'''+@productName+''''+CASE WHEN @catalog IS NOT NULL AND @catalog <> N'''' THEN ', @catalog=N'''+@catalog+'''' ELSE '''' END

    -- NOTE: sp_addlinkedsrvlogin is intentionally NOT emitted here.
    -- The Go layer will append the correct login statement per linked server
    -- based on GET_LINKSERVERS_META (useself flag + remote_user) and the
    -- encrypted remote-credential list passed in via CloneLinkserversParam.

    SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC master.dbo.sp_serveroption @server=N'''+@servername+''', @optname=N''collation compatible'', @optvalue=N'''+CASE @collationcompatible WHEN 0 THEN 'false' ELSE 'true' END+'''' 

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

    -- persist this server's skeleton SQL as an independent row
    INSERT INTO #linkserver_out (name, linkserver_sql) VALUES (@servername, @sql)

    FETCH NEXT FROM LinkserverNameCur INTO @servername, @id
END
CLOSE LinkserverNameCur
DEALLOCATE LinkserverNameCur

SELECT name, linkserver_sql FROM #linkserver_out ORDER BY name
DROP TABLE #linkserver_out
`
