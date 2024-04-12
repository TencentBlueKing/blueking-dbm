USE MASTER
SET QUOTED_IDENTIFIER ON
SET NOCOUNT ON
GO

DECLARE @SERVERNAME VARCHAR(100),@SQLSERVERACCOUNT VARCHAR(100)
SET @SERVERNAME = CAST(SERVERPROPERTY('SERVERNAME') AS VARCHAR(100))
IF CHARINDEX('\',@SERVERNAME) > 0
	SET @SQLSERVERACCOUNT = SUBSTRING(@SERVERNAME,1,CHARINDEX('\',@SERVERNAME)-1)+'\sqlserver'
ELSE 
	SET @SQLSERVERACCOUNT = @SERVERNAME+'\sqlserver'
DECLARE @SQL VARCHAR(MAX) = 
'IF SUSER_SID('''+@SQLSERVERACCOUNT+''') IS NULL
	CREATE LOGIN ['+@SQLSERVERACCOUNT+'] FROM WINDOWS
EXEC SP_ADDSRVROLEMEMBER ['+@SQLSERVERACCOUNT+'],''sysadmin'''
--PRINT(@SQL)
EXEC(@SQL)
GO

EXEC SP_CONFIGURE 'SHOW ADVANCED OPTIONS',1
GO
RECONFIGURE;
GO

EXEC SP_CONFIGURE 'CROSS DB OWNERSHIP CHAINING',1
EXEC SP_CONFIGURE 'AGENT XPS',1
exec SP_CONFIGURE 'remote access',1
EXEC SP_CONFIGURE 'REMOTE ADMIN CONNECTIONS',0
EXEC SP_CONFIGURE 'XP_CMDSHELL',1
EXEC SP_CONFIGURE 'C2 AUDIT MODE',0
EXEC SP_CONFIGURE 'RECOVERY INTERVAL',0
EXEC SP_CONFIGURE 'FILL FACTOR (%)',80
EXEC SP_CONFIGURE 'ALLOW UPDATES',0
EXEC SP_CONFIGURE 'BACKUP COMPRESSION DEFAULT',1
EXEC SP_CONFIGURE 'AD HOC DISTRIBUTED QUERIES',1
EXEC SP_CONFIGURE 'SMO and DMO XPs',1

GO
RECONFIGURE
GO

--EXEC SP_CONFIGURE 'SHOW ADVANCED OPTIONS',0
--GO
--RECONFIGURE;
--GO

--modify modeldb
IF EXISTS(select 1 from model.sys.database_files where name='modeldev' and size/128<500)
	ALTER DATABASE MODEL MODIFY FILE (NAME = 'modeldev',SIZE = 500MB,FILEGROWTH = 512MB)
IF EXISTS(select 1 from model.sys.database_files where name='modellog' and size/128<500)
	ALTER DATABASE MODEL MODIFY FILE (NAME = 'modellog',SIZE = 500MB,FILEGROWTH = 512MB)
GO

DECLARE @SQL VARCHAR(MAX)
SELECT @SQL = ISNULL(@SQL+CHAR(13),'')+'ALTER DATABASE TEMPDB MODIFY FILE (NAME = '''+name+''',SIZE = 1GB,FILEGROWTH = 512MB);'
FROM SYS.MASTER_FILES where database_id =2
EXEC(@SQL)
GO

DECLARE @physical_path VARCHAR(1000)
SELECT @physical_path=replace(physical_name,'\tempdb.mdf','') FROM SYS.MASTER_FILES where database_id =2 and name='tempdev'

--add tempdb datafile by logical cpu number
DECLARE @SQL VARCHAR(MAX)
;WITH T_INDEXNO AS
(
SELECT NUMBER AS INDEXNO
FROM SYS.DM_OS_SYS_INFO A,MASTER.DBO.SPT_VALUES B
WHERE B.TYPE = 'P' AND B.NUMBER > 1
	AND B.NUMBER <= A.CPU_COUNT
),T_TEMP AS
(
SELECT REPLACE(NAME,'temp','') AS INDEXNO
FROM SYS.MASTER_FILES
WHERE LEN(REPLACE(NAME,'temp','')) >= 1 AND DATABASE_ID = 2 AND TYPE = 0 AND name not in('tempdev')
)
SELECT @SQL = ISNULL(@SQL+CHAR(13),'')+'ALTER DATABASE tempdb ADD FILE(NAME = ''temp'+LTRIM(A.INDEXNO)+''',FILENAME = '''+@physical_path+'\tempdb_mssql_'+LTRIM(A.INDEXNO)+'.ndf'',SIZE =1GB,FILEGROWTH = 512MB);'
FROM T_INDEXNO A LEFT JOIN T_TEMP B ON A.INDEXNO = B.INDEXNO
WHERE B.INDEXNO IS NULL
PRINT(@SQL)
EXEC(@SQL)
GO

--modfiy agent log setting
EXEC MSDB.DBO.SP_SET_SQLAGENT_PROPERTIES @JOBHISTORY_MAX_ROWS = 43200,@JOBHISTORY_MAX_ROWS_PER_JOB = 4320;
GO

USE MASTER
GO
REVOKE EXECUTE ON xp_dirtree FROM PUBLIC
REVOKE EXECUTE ON xp_grantlogin FROM PUBLIC
REVOKE EXECUTE ON xp_revokelogin FROM PUBLIC
GO


USE MASTER
SET QUOTED_IDENTIFIER ON
SET NOCOUNT ON
GO
--**************************************** 结束当前启用的跟踪 *******************************
DECLARE @SQL VARCHAR(8000)
SELECT @SQL = ISNULL(@SQL+'
','')+'EXEC SP_TRACE_SETSTATUS '+LTRIM(ID)+',0;EXEC SP_TRACE_SETSTATUS '+LTRIM(ID)+',2;'
FROM SYS.TRACES A
WHERE A.IS_DEFAULT = 0
--PRINT(@SQL)
EXEC(@SQL)
GO

--****************************************** 结束连接 ************************************
DECLARE @SQL VARCHAR(MAX)
SELECT @SQL = ISNULL(@SQL+CHAR(13),'')+'KILL '+LTRIM(SPID)
FROM SYS.SYSPROCESSES
WHERE DBID = DB_ID('Monitor')
	AND SPID > 50
--PRINT(@SQL)
EXEC(@SQL)
GO

IF DB_ID('Monitor') IS NOT NULL
BEGIN
	ALTER DATABASE Monitor SET SINGLE_USER WITH ROLLBACK IMMEDIATE
	DROP DATABASE Monitor
END

--****************************************** DATABASE ****************************************
USE MASTER
GO
CREATE DATABASE Monitor
GO
ALTER DATABASE [Monitor] SET RECOVERY SIMPLE
GO

--****************************************** LOGIN ****************************************


--****************************************** PRINCIPAL ****************************************


--****************************************** TABLE ****************************************

USE [Monitor]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TRACE_TSQL]') AND type in (N'U'))
DROP TABLE [dbo].[TRACE_TSQL]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TRACE_CURRENT_TRACEINFO]') AND type in (N'U'))
DROP TABLE [dbo].[TRACE_CURRENT_TRACEINFO]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MONITOR_INSANCE_COUNTER]') AND type in (N'U'))
DROP TABLE [dbo].[MONITOR_INSANCE_COUNTER]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MIRRORING_FILTER]') AND type in (N'U'))
DROP TABLE [dbo].[MIRRORING_FILTER]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[BACKUP_TRACE]') AND type in (N'U'))
DROP TABLE [dbo].[BACKUP_TRACE]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[BACKUP_FILTER]') AND type in (N'U'))
DROP TABLE [dbo].[BACKUP_FILTER]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[BACKUP_COMMON_TABLE]') AND type in (N'U'))
DROP TABLE [dbo].[BACKUP_COMMON_TABLE]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[AUTO_GRANT]') AND type in (N'U'))
DROP TABLE [dbo].[AUTO_GRANT]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[APP_SETTING]') AND type in (N'U'))
DROP TABLE [dbo].[APP_SETTING]
GO

/****** Object:  Table [dbo].[APP_SETTING]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[APP_SETTING](
	[APP] [varchar](100) NOT NULL,
	[FULL_BACKUP_PATH] [varchar](100) NOT NULL,
	[LOG_BACKUP_PATH] [varchar](100) NOT NULL,
	[KEEP_FULL_BACKUP_DAYS] [int] NOT NULL,
	[KEEP_LOG_BACKUP_DAYS] [int] NOT NULL,
	[FULL_BACKUP_MIN_SIZE_MB] [int] NOT NULL,
	[LOG_BACKUP_MIN_SIZE_MB] [int] NOT NULL,
	[UPLOAD] [int] NOT NULL,
	[MD5] [int] NOT NULL,
	[CLUSTER_ID] [bigint] NULL,
	[CLUSTER_DOMAIN] [varchar](100) NULL,
	[IP] [varchar](100) NULL,
	[PORT] [varchar](100) NULL,
	[ROLE] [varchar](100) NULL,
	[MASTER_IP] [varchar](100) NULL,
	[MASTER_PORT] [varchar](100) NULL,
	[SYNCHRONOUS_MODE] [varchar](100) NULL,
	[BK_BIZ_ID] [varchar](100) NULL,
	[BK_CLOUD_ID] [varchar](100) NULL,
	[VERSION] [varchar](100) NULL,
	[BACKUP_TYPE] [varchar](100) NULL,
	[DATA_SCHEMA_GRANT] [varchar](100) NULL,
	[TIME_ZONE] [varchar](100) NULL,
	[CHARSET] [varchar](100) NULL,
	[BACKUP_CLIENT_PATH] [varchar](1000) NULL,
	[BACKUP_STORAGE_TYPE] [varchar](100) NULL,
	[FULL_BACKUP_REPORT_PATH] [varchar](1000) NULL,
	[LOG_BACKUP_REPORT_PATH] [varchar](1000) NULL,
	[FULL_BACKUP_FILETAG] [varchar](100) NULL,
	[LOG_BACKUP_FILETAG] [varchar](100) NULL,
	[SHRINK_SIZE] [bigint] NULL,
	[RESTORE_PATH] [varchar](1000) NULL,
	[LOG_SEND_QUEUE] [bigint] NULL,
	[TRACEON] [tinyint] NULL,
	[SLOW_DURATION] [int] NULL,
	[SLOW_SAVEDAY] [int] NULL,
	[UPDATESTATS] [tinyint] NULL
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[AUTO_GRANT]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[AUTO_GRANT](
	[ACCOUNT] [varchar](200) NOT NULL,
	[GRANT_DB] [varchar](200) NULL,
	[GRANT_TYPE] [varchar](200) NULL,
	[UPDATE_TIME] [datetime] NULL
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[BACKUP_COMMON_TABLE]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BACKUP_COMMON_TABLE](
	[BLOCK] [varchar](8000) NULL
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[BACKUP_FILTER]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BACKUP_FILTER](
	[NAME] [varchar](100) NOT NULL
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[BACKUP_TRACE]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[BACKUP_TRACE](
	[BACKUP_ID] [varchar](1000) NULL,
	[DBNAME] [varchar](100) NOT NULL,
	[PATH] [varchar](1000) NOT NULL,
	[FILENAME] [varchar](1000) NOT NULL,
	[TYPE] [int] NOT NULL,
	[STARTTIME] [datetime] NOT NULL,
	[ENDTIME] [datetime] NOT NULL,
	[DURATION]  AS (datediff(second,[STARTTIME],[ENDTIME])),
	[FILESIZE] [bigint] NULL,
	[MD5CODE] [varchar](100) NOT NULL,
	[SUCCESS] [int] NOT NULL,
	[UPLOADED] [int] NOT NULL,
	[WRITETIME] [datetime] NOT NULL,
 CONSTRAINT [PK_BACKUP_TRACE_FILENAME] PRIMARY KEY NONCLUSTERED 
(
	[FILENAME] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, FILLFACTOR = 80) ON [PRIMARY]
) ON [PRIMARY]

GO

/****** Object:  Index [IDX_CL_BACKUP_TRACE_STARTTIME]    Script Date: 2024/4/7 16:15:50 ******/
CREATE CLUSTERED INDEX [IDX_CL_BACKUP_TRACE_STARTTIME] ON [dbo].[BACKUP_TRACE]
(
	[STARTTIME] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, FILLFACTOR = 80) ON [PRIMARY]
GO

CREATE INDEX [IDX_CL_BACKUP_TRACE_BACKUP_ID] ON [dbo].[BACKUP_TRACE]
(
	[BACKUP_ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, FILLFACTOR = 80) ON [PRIMARY]
GO

/****** Object:  Table [dbo].[MIRRORING_FILTER]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[MIRRORING_FILTER](
	[NAME] [varchar](100) NOT NULL,
 CONSTRAINT [PK_MIRRORING_FILTER] PRIMARY KEY CLUSTERED 
(
	[NAME] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[MONITOR_INSANCE_COUNTER]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[MONITOR_INSANCE_COUNTER](
	[COUNTER_SHORT_NAME] [varchar](100) NOT NULL,
	[OBJECT_NAME] [varchar](100) NOT NULL,
	[COUNTER_NAME] [varchar](100) NOT NULL,
	[INSTANCE_NAME] [varchar](100) NOT NULL,
	[COMPUTE_INTERVAL] [int] NOT NULL
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[TRACE_CURRENT_TRACEINFO]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[TRACE_CURRENT_TRACEINFO](
	[STARTTIME] [datetime] NOT NULL,
	[TRACEID] [int] NOT NULL,
	[TRACEFILE] [varchar](100) NOT NULL
) ON [PRIMARY]

GO

/****** Object:  Table [dbo].[TRACE_TSQL]    Script Date: 2024/4/7 16:15:50 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[TRACE_TSQL](
	[SQLTXT] [varchar](8000) NULL,
	[SQLCHECKSUM] [bigint] NULL,
	[TEXTDATA] [varchar](8000) NULL,
	[APPLICATIONNAME] [varchar](5000) NULL,
	[NTUSERNAME] [varchar](5000) NULL,
	[LOGINNAME] [varchar](5000) NULL,
	[DURATION] [bigint] NOT NULL,
	[STARTTIME] [datetime] NULL,
	[ENDTIME] [datetime] NULL,
	[READS] [bigint] NULL,
	[WRITES] [bigint] NULL,
	[CPU] [int] NULL,
	[SERVERNAME] [varchar](500) NULL,
	[ERROR] [bigint] NULL,
	[OBJECTID] [bigint] NULL,
	[OBJECTNAME] [varchar](5000) NULL,
	[DATABASENAME] [varchar](1000) NULL,
	[ROWCOUNTS] [bigint] NULL
) ON [PRIMARY]

GO

/****** Object:  Index [IDX_CL_TRACETSQL_STARTTIME]    Script Date: 2024/4/7 16:15:50 ******/
CREATE CLUSTERED INDEX [IDX_CL_TRACETSQL_STARTTIME] ON [dbo].[TRACE_TSQL]
(
	[STARTTIME] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO

SET ANSI_PADDING ON

GO

/****** Object:  Index [IX_AUTO_GRANT]    Script Date: 2024/4/7 16:15:50 ******/
CREATE UNIQUE NONCLUSTERED INDEX [IX_AUTO_GRANT] ON [dbo].[AUTO_GRANT]
(
	[ACCOUNT] ASC,
	[GRANT_DB] ASC,
	[GRANT_TYPE] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, FILLFACTOR = 80) ON [PRIMARY]
GO

/****** Object:  Index [IX_COMPUTE_INTERVAL]    Script Date: 2024/4/7 16:15:50 ******/
CREATE NONCLUSTERED INDEX [IX_COMPUTE_INTERVAL] ON [dbo].[MONITOR_INSANCE_COUNTER]
(
	[COMPUTE_INTERVAL] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, FILLFACTOR = 80) ON [PRIMARY]
GO

SET ANSI_PADDING ON

GO

/****** Object:  Index [IX_COUNTER_NAME]    Script Date: 2024/4/7 16:15:50 ******/
CREATE NONCLUSTERED INDEX [IX_COUNTER_NAME] ON [dbo].[MONITOR_INSANCE_COUNTER]
(
	[COUNTER_NAME] ASC,
	[INSTANCE_NAME] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, FILLFACTOR = 80) ON [PRIMARY]
GO

/****** Object:  Index [IDX_NC_TRACETSQL_SQLCHECKSUM]    Script Date: 2024/4/7 16:15:50 ******/
CREATE NONCLUSTERED INDEX [IDX_NC_TRACETSQL_SQLCHECKSUM] ON [dbo].[TRACE_TSQL]
(
	[SQLCHECKSUM] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO

ALTER TABLE [dbo].[MONITOR_INSANCE_COUNTER] ADD  CONSTRAINT [DF_MONITOR_INSANCE_COUNTER_COMPUTE_INTERVAL]  DEFAULT ((0)) FOR [COMPUTE_INTERVAL]
GO

ALTER TABLE [dbo].[APP_SETTING]  WITH CHECK ADD  CONSTRAINT [CK_FULLBACKUPMINSIZEMB] CHECK  (([FULL_BACKUP_MIN_SIZE_MB]>(10240)))
GO

ALTER TABLE [dbo].[APP_SETTING] CHECK CONSTRAINT [CK_FULLBACKUPMINSIZEMB]
GO

ALTER TABLE [dbo].[APP_SETTING]  WITH CHECK ADD  CONSTRAINT [CK_LOGBACKUPMINSIZEMB] CHECK  (([LOG_BACKUP_MIN_SIZE_MB]>(10240)))
GO

ALTER TABLE [dbo].[APP_SETTING] CHECK CONSTRAINT [CK_LOGBACKUPMINSIZEMB]
GO

--****************************************** VIEW ****************************************
USE [Monitor]
GO

/****** Object:  View [dbo].[BACKUP_DBLIST]    Script Date: 2024/4/7 14:26:11 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE VIEW [dbo].[BACKUP_DBLIST]
AS
	SELECT A.DATABASE_ID,A.NAME
	FROM SYS.DATABASES A
	WHERE A.DATABASE_ID > 4
		AND A.IS_READ_ONLY = 0
		AND A.IS_DISTRIBUTOR = 0
		AND A.STATE = 0
		AND A.NAME NOT LIKE '%AUTOREST'
		AND A.NAME NOT IN('Monitor')
		AND NOT EXISTS(SELECT 1 FROM DBO.BACKUP_FILTER B
			WHERE A.NAME = B.NAME)

GO

/****** Object:  View [dbo].[CUSTOMER_DBLIST]    Script Date: 2024/4/7 14:26:11 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE VIEW [dbo].[CUSTOMER_DBLIST]
AS
	SELECT A.DATABASE_ID,A.NAME
	FROM SYS.DATABASES A
	WHERE A.DATABASE_ID > 4
		AND A.IS_READ_ONLY = 0
		AND A.IS_DISTRIBUTOR = 0
		AND A.STATE = 0
		AND A.NAME <> 'MONITOR'

GO

--****************************************** FUN ****************************************
IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[funConvertVarCharToVarBinary]') AND type in (N'FN', N'IF', N'TF', N'FS', N'FT'))
DROP FUNCTION [dbo].[funConvertVarCharToVarBinary]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[funConvertVarBinaryToVarChar]') AND type in (N'FN', N'IF', N'TF', N'FS', N'FT'))
DROP FUNCTION [dbo].[funConvertVarBinaryToVarChar]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[SplitStringByRow]') AND type in (N'FN', N'IF', N'TF', N'FS', N'FT'))
DROP FUNCTION [dbo].[SplitStringByRow]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE FUNCTION [dbo].[funConvertVarBinaryToVarChar]
(@vbnInput varbinary(512))  
RETURNS varchar(1024)
AS  
BEGIN
	declare @chvOutput varchar(1024)
	set @chvOutput = ''
	declare @intLen int	
	set @intLen = datalength(@vbnInput)
	declare @intPos int
	set @intPos = 1
	declare @bytByte binary
	declare @intTmp tinyint
	declare @chvTmp varchar(2)
	while @intPos <= @intLen
	begin
		set @bytByte = substring(@vbnInput, @intPos, 1)
		-- 第一个字符
		set @intTmp = @bytByte / 16
		if @intTmp >= 10
			set @chvTmp = 
				case @intTmp
					when 10 then 'A'
					when 11 then 'B'
					when 12 then 'C'
					when 13 then 'D'
					when 14 then 'E'
					when 15 then 'F'
				end
		else
			set @chvTmp = cast(@intTmp as char(1))
		-- 第二个字符
		set @intTmp = @bytByte - @intTmp * 16
		if @intTmp >= 10
			set @chvTmp = @chvTmp +
				case @intTmp
					when 10 then 'A'
					when 11 then 'B'
					when 12 then 'C'
					when 13 then 'D'
					when 14 then 'E'
					when 15 then 'F'
				end
		else
			set @chvTmp = @chvTmp + cast(@intTmp as char(1))
		set @chvOutput = @chvOutput + @chvTmp
		set @intPos = @intPos + 1
	end
	return @chvOutput
END
GO

/****** Object:  UserDefinedFunction [dbo].[funConvertVarCharToVarBinary]    Script Date: 2021/11/8 15:06:20 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE FUNCTION [dbo].[funConvertVarCharToVarBinary]
(@chvInput varchar(1024))  
RETURNS varbinary(512)--- varchar(20)
AS  
BEGIN
	declare @binOutput varbinary(512)
	if substring(@chvInput,1,2)='0x'
	set @chvInput = substring(@chvInput,3,datalength(@chvInput)-2) --去掉0x
	---set @binOutput = ''
	declare @intLen int	
	set @intLen = datalength(@chvInput)
	declare @intPos int
	set @intPos = 1
	declare @tinyint1 tinyint
	declare @tinyint2 tinyint
	declare @tinyintBin binary(1)
	declare @intTmp tinyint
	declare @chvTmp varchar(2)
	declare @charTmp1 varchar(1)
	declare @charTmp2 varchar(1)	
	while @intPos <= @intLen
	begin
		set @chvTmp = substring(@chvInput, @intPos, 2)
		
		set @charTmp1=substring(@chvTmp,1,1)
		set @tinyint1=
			case @charTmp1
				when '' then 0
				when 'A' then 10*16
				when 'B' then 11*16
				when 'C' then 12*16
				when 'D' then 13*16
				when 'E' then 14*16
				when 'F' then 15*16
				else cast(@charTmp1 as tinyint)*16
			end
		
		set @charTmp2=substring(@chvTmp,2,1)
		set @tinyint2=
			case @charTmp2
				when 'A' then 10
				when 'B' then 11
				when 'C' then 12
				when 'D' then 13
				when 'E' then 14
				when 'F' then 15
				else cast(@charTmp2 as tinyint)
			end
		set @tinyintBin=cast(@tinyint1+@tinyint2 as binary(1))
		if @intPos=1 set @binOutput=@tinyintBin
		else set @binOutput=@binOutput+@tinyintBin
		set @intPos = @intPos + 2
	end
	return @binOutput
END
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE FUNCTION [dbo].[SplitStringByRow]
(
    @InputString NVARCHAR(MAX),
    @Delimiter NVARCHAR(10)
)
RETURNS @Result TABLE
(
    RowValue NVARCHAR(MAX)
)
AS
BEGIN
    DECLARE @Value NVARCHAR(MAX)
    WHILE CHARINDEX(@Delimiter, @InputString) > 0
    BEGIN
        SET @Value = SUBSTRING(@InputString, 1, CHARINDEX(@Delimiter, @InputString) - 1)
        INSERT INTO @Result (RowValue) VALUES (@Value)
        SET @InputString = SUBSTRING(@InputString, CHARINDEX(@Delimiter, @InputString) + LEN(@Delimiter), LEN(@InputString))
    END
    IF LEN(@InputString) > 0
    BEGIN
        INSERT INTO @Result (RowValue) VALUES (@InputString)
    END
    RETURN
END
GO

--****************************************** SP ****************************************

USE [Monitor]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TOOL_GET_IPPORT]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[TOOL_GET_IPPORT]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TOOL_CHECK_DISK_FREE_SIZE]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[TOOL_CHECK_DISK_FREE_SIZE]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TOOL_BACKUP_DATABASE_OPERATOR]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[TOOL_BACKUP_DATABASE_OPERATOR]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TOOL_BACKUP_DATABASE]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[TOOL_BACKUP_DATABASE]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_Suspend]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_Suspend]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_SafetyOff]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_SafetyOff]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_Resume]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_Resume]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_Remove]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_Remove]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_LossOver]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_LossOver]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_FailOver]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_FailOver]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[Sys_AutoSwitch_DrToDb]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[Sys_AutoSwitch_DrToDb]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[mssql_exporter]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[mssql_exporter]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_UPDATESTATS]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[JOB_UPDATESTATS]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_TRACE]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[JOB_TRACE]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_SNAPSHOT]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[JOB_SNAPSHOT]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_MONITOR_FILTER]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[JOB_MONITOR_FILTER]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_AUTO_GRANT]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[JOB_AUTO_GRANT]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TOOL_CHANGE_DBOWNER]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[TOOL_CHANGE_DBOWNER]
GO

/****** Object:  StoredProcedure [dbo].[JOB_AUTO_GRANT]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROC [dbo].[JOB_AUTO_GRANT]
AS
BEGIN
	SET NOCOUNT ON

	DECLARE @DBLIST VARCHAR(8000),@SQL VARCHAR(MAX)

	IF OBJECT_ID('tempdb.dbo.#dblist','U') IS NOT NULL
		DROP TABLE #dblist
	CREATE TABLE #dblist(name varchar(200))

	insert into #dblist select name from master.sys.databases where database_id>4 and name not in('Monitor') and state=0 and is_read_only=0 and name not like 'distribution%' and name not like '%_dr' and create_date>dateadd(MI,-5,GETDATE())

	IF NOT EXISTS(SELECT 1 FROM #dblist)
		RETURN 1

	DECLARE @ACCOUNT VARCHAR(200),@GRANT_DB VARCHAR(200),@GRANT_TYPE VARCHAR(200)
	DECLARE list_cur cursor static forward_only Read_only for 
	select ACCOUNT,GRANT_DB,GRANT_TYPE from [Monitor].[dbo].[AUTO_GRANT] where ACCOUNT IN(select name from master.sys.sql_logins where is_disabled=0)
	OPEN list_cur;

	FETCH NEXT FROM list_cur INTO @ACCOUNT,@GRANT_DB,@GRANT_TYPE
	WHILE @@FETCH_STATUS = 0
	BEGIN
		SET @SQL = ''
		SELECT @SQL = ISNULL(@SQL+'','')+'USE ['+name+'] IF EXISTS (SELECT * FROM sys.database_principals WHERE name = N'''+@ACCOUNT+''') BEGIN EXEC ['+name+'].dbo.sp_change_users_login ''AUTO_FIX'','''+@ACCOUNT+''' END ELSE BEGIN CREATE USER ['+@ACCOUNT+'] FOR LOGIN ['+@ACCOUNT+'] END;EXEC sp_addrolemember N'''+@GRANT_TYPE+''', N'''+@ACCOUNT+''';'
		from master.sys.databases where name like @GRANT_DB and name in(select name from #dblist)
		PRINT(@SQL)
		EXEC(@SQL)

		FETCH NEXT FROM list_cur INTO @ACCOUNT,@GRANT_DB,@GRANT_TYPE;
	END
	CLOSE list_cur;
	DEALLOCATE list_cur;
		
END


GO

/****** Object:  StoredProcedure [dbo].[JOB_MONITOR_FILTER]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROC [dbo].[JOB_MONITOR_FILTER]
WITH RECOMPILE
AS
BEGIN
	SET NOCOUNT ON

	--UPLOAD DATA
	DECLARE @IP VARCHAR(20),@PORT VARCHAR(20),@SQL VARCHAR(MAX)
	EXEC MONITOR.DBO.TOOL_GET_IPPORT @IP OUTPUT,@PORT OUTPUT
	
	IF EXISTS(SELECT 1 FROM MONITOR.DBO.APP_SETTING where TRACEON=1)
	BEGIN
		IF EXISTS(select 1 from sys.dm_os_sys_info where datediff(mi,sqlserver_start_time,getdate())<=5)
		BEGIN
			IF OBJECT_ID('TEMPDB.DBO.#TMP_TRACESTATUS','U') IS NOT NULL
				DROP TABLE #TMP_TRACESTATUS

			CREATE TABLE #TMP_TRACESTATUS(traceflag bigint,status bigint,global bigint,session bigint)

			INSERT INTO #TMP_TRACESTATUS
			EXEC('DBCC TRACESTATUS (1118,1204,1222,3605, -1);')

			IF NOT EXISTS(SELECT 1 FROM #TMP_TRACESTATUS where global=1)
				DBCC TRACEON (1118,1204,1222,3605, -1);
		END
	END
	
	EXEC TOOL_CHANGE_DBOWNER
	
	/*
	IF EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING where mirroring_safety_level=2)
	BEGIN
		SELECT @SQL = ISNULL(@SQL+'','')+'ALTER DATABASE ['+b.name+'] SET SAFETY OFF;'
		FROM SYS.DATABASE_MIRRORING a left join sys.databases b on a.database_id=b.database_id
		where mirroring_safety_level=2
		EXEC(@SQL)
	END
	
	IF EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING WHERE MIRRORING_STATE IN (0,2))
	BEGIN
		exec monitor.dbo.Sys_AutoSwitch_Suspend null
		exec monitor.dbo.Sys_AutoSwitch_Resume null
	END
	
	IF EXISTS(SELECT 1 FROM master.sys.dm_os_performance_counters 
	WHERE object_name LIKE '%Database Mirroring%' 
	AND counter_name='Redo Queue KB' and cntr_value>1048576) 
	OR EXISTS(SELECT 1
		FROM SYS.MASTER_FILES A,MONITOR.DBO.BACKUP_DBLIST B
		WHERE A.DATABASE_ID  = B.DATABASE_ID
			AND A.TYPE = 1
			AND SIZE > 30*1024*1024/8)
	BEGIN
		IF EXISTS(select 1 from [master].[sys].[database_mirroring_endpoints])
		BEGIN
			ALTER ENDPOINT [endpoint_mirroring] STATE = STOPPED
			ALTER ENDPOINT [endpoint_mirroring] STATE = STARTED
		END
	END
	*/
	    /* self-healing MIRRORING_LOG_SEND_QUEUE_KB */
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+';'+CHAR(13),'')+'

		IF EXISTS(SELECT 1 FROM master.sys.database_mirroring where database_id='+convert(varchar,A.database_id)+')


				ALTER DATABASE ['+A.NAME+'] set partner off;
		USE MASTER ALTER DATABASE ['+A.NAME+'] SET RECOVERY SIMPLE WITH NO_WAIT;
		USE ['+A.NAME+'] DBCC SHRINKFILE ('''+B.NAME+''',0,TRUNCATEONLY);
		USE MASTER ALTER DATABASE ['+A.NAME+'] SET RECOVERY FULL WITH NO_WAIT;
		'
		FROM MASTER.SYS.DATABASES A,MASTER.SYS.MASTER_FILES B
		WHERE A.DATABASE_ID > 4
		AND A.NAME in (
		SELECT a.instance_name
		FROM MASTER.SYS.DM_OS_PERFORMANCE_COUNTERS A,monitor.DBO.APP_SETTING B
		WHERE A.OBJECT_NAME LIKE '%DATABASE MIRRORING%'
				AND A.COUNTER_NAME='LOG SEND QUEUE KB'
			AND A.INSTANCE_NAME != '_TOTAL'
				AND A.CNTR_VALUE > B.LOG_SEND_QUEUE*10
				AND EXISTS(SELECT 1 FROM MASTER.SYS.DATABASE_MIRRORING C WHERE C.MIRRORING_ROLE = 1)
		)

		AND A.DATABASE_ID = B.DATABASE_ID
		AND B.TYPE = 1
		-- print(@SQL)
		EXEC(@SQL)
	
END


GO

/****** Object:  StoredProcedure [dbo].[JOB_SNAPSHOT]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [dbo].[JOB_SNAPSHOT]
@type tinyint = 0
AS
BEGIN

	SET NOCOUNT ON
	
	declare @dbid int,@db sysname,@dr sysname, @logic sysname,@has_monitor tinyint,@msg varchar(2000),@cmd varchar(max),@cmd2 varchar(max)

	declare @port sysname
	exec monitor.dbo.TOOL_GET_IPPORT null,@port output

	IF datepart(hh,getdate())>=1 and @type=1 and NOT EXISTS(SELECT 1 FROM APP_SETTING WHERE APP='qqhx')
		return

	declare @exec_time datetime
	set @exec_time=getdate()

	declare @version bigint,@is_alwayson_flag tinyint
	set @version=convert(bigint,DATABASEPROPERTYEX('master','version'))
	set @is_alwayson_flag=0

	IF OBJECT_ID('TEMPDB.DBO.#tmp_alwayson','U') IS NOT NULL
		DROP TABLE #tmp_alwayson
	create table #tmp_alwayson(name varchar(200))

	IF OBJECT_ID('TEMPDB.DBO.#tmp_dblist','U') IS NOT NULL
		DROP TABLE #tmp_dblist
	create table #tmp_dblist(dbid int,name varchar(200),flag tinyint)

	IF @version>=869
		exec('insert into #tmp_alwayson select name from sys.availability_groups')

	IF exists(select 1 from #tmp_alwayson)
		set @is_alwayson_flag=1

	if @is_alwayson_flag=1
		exec('insert into #tmp_dblist select database_id,name,0 from master.sys.databases where database_id>4 and name not in(''monitor'') and name not like ''%_dr'' and database_id in(SELECT database_id from sys.dm_hadr_database_replica_states where is_local=1 and synchronization_state=1)')
	else
		insert into #tmp_dblist select database_id,name,0 from master.sys.databases where database_id>4 and name not in('monitor') and name not like '%_dr' and database_id in(select database_id from master.sys.database_mirroring where mirroring_guid is not null and mirroring_state=4)

	declare @i int,@fileid int
	declare @filename sysname
	set @i=1
	while @i<=10
	begin
		declare cur cursor for
		select dbid,name from #tmp_dblist where flag=0
		open cur
		while 1=1
		begin
		fetch next from cur into @dbid,@db
			if @@FETCH_STATUS<>0 break
			set @dr=@db+'_dr'

			IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = @dr and create_date>=@exec_time)
			BEGIN
				IF EXISTS (SELECT name FROM sys.databases WHERE name = @dr)
				BEGIN
					SET @cmd='DROP DATABASE '+@dr
					EXEC (@cmd)
					
					SET @cmd2='EXEC MASTER.DBO.xp_cmdshell ''del /q d:\gamedb\'+@dr+'.'+@port+'.*.spst'';'
					EXEC (@cmd2)
				END

				select @filename=null,@cmd='',@fileid=0,@cmd='CREATE DATABASE '+@dr+' ON '
				declare cur1 cursor for select name from sys.master_files where database_id=@dbid and type_desc='ROWS' and state_desc='ONLINE'
				open cur1
				while 1=1
				begin
					set @filename=null
					fetch next from cur1 into @filename
					if @@FETCH_STATUS<>0 break	    
					select @cmd=@cmd+'(NAME='''+@filename+''',FILENAME='''+'D:\gamedb\'+@dr+'.'+@port+'.'+CONVERT(varchar,@fileid)+'.spst'+'''),'
						,@fileid=@fileid+1
				end
				close cur1
				deallocate cur1	
    
				set @cmd=left(@cmd,len(@cmd)-1)+' AS SNAPSHOT OF '+@db    
				
				BEGIN TRY
					EXEC (@cmd)
				END TRY
				BEGIN CATCH
					SET @cmd2='EXEC MASTER.DBO.xp_cmdshell ''del /q d:\gamedb\'+@dr+'.'+@port+'.*.spst'';'
					EXEC (@cmd2)
					
					EXEC (@cmd)
				END CATCH
			END
			ELSE
			BEGIN
				update #tmp_dblist set flag=1 where dbid=@dbid
			END
		END
		close cur
		deallocate cur  
    
		set @i=@i+1

		waitfor delay '00:00:02'
	end
END



GO

/****** Object:  StoredProcedure [dbo].[JOB_TRACE]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [dbo].[JOB_TRACE]
@DELETE_OLD_TRACE_FILE INT --是否删除旧跟踪文件 1:删除/0:保留
AS
BEGIN
	SET NOCOUNT ON
	
	--定义启动跟踪的失败的代码
	DECLARE @RESULT_CODE INT
	--定义跟踪ID
	DECLARE @TRACEID INT
	--定义跟踪文件的最大容量
	DECLARE @MAXFILESIZE BIGINT
	--定义跟踪文件存放的路径
	DECLARE @TRACEFILE NVARCHAR(1000)
	--定义旧跟踪文件存放的路径
	DECLARE @OLDTRACEFILE NVARCHAR(1000)
	--定义命令变量
	DECLARE @CMD VARCHAR(100)
	--定义SQL执行时长筛选值(微秒)
	DECLARE @FILTERDURATION BIGINT,@KEEPDATADAYS INT
	
	IF OBJECT_ID('DBO.TRACE_SETTING','U') IS NOT NULL
	BEGIN
		SELECT @FILTERDURATION = SLOW_DURATION*1000,@KEEPDATADAYS=SLOW_SAVEDAY FROM DBO.APP_SETTING
	END

	SELECT @FILTERDURATION = ISNULL(@FILTERDURATION,1000000),@KEEPDATADAYS = ISNULL(@KEEPDATADAYS,60)
		
	
	--停止当前跟踪
	IF EXISTS(SELECT 1 FROM DBO.TRACE_CURRENT_TRACEINFO)
	BEGIN
		IF EXISTS(SELECT 1 FROM SYS.TRACES A,DBO.TRACE_CURRENT_TRACEINFO B WHERE A.ID = B.TRACEID)
		BEGIN
			SELECT @TRACEID = TRACEID,@OLDTRACEFILE = TRACEFILE FROM DBO.TRACE_CURRENT_TRACEINFO

			EXEC SP_TRACE_SETSTATUS @TRACEID,0
			EXEC SP_TRACE_SETSTATUS @TRACEID,2
		END
		TRUNCATE TABLE DBO.TRACE_CURRENT_TRACEINFO
	END
	--建立文件夹
	EXEC XP_CMDSHELL 'MD C:\TRACE',NO_OUTPUT

	--开始新的跟踪
	BEGIN
		--对变量赋值,单位:MB
		SET @MAXFILESIZE = 20000
		SET @TRACEFILE = N'C:\TRACE\TRACE_'+@@SERVICENAME+'_'+REPLACE(REPLACE(REPLACE(CONVERT(NVARCHAR(20),GETDATE(),120),'-',''),' ',''),':','')

		--初始化跟踪
		EXEC @RESULT_CODE = SP_TRACE_CREATE @TRACEID OUTPUT,2,@TRACEFILE,@MAXFILESIZE,NULL
		--出错则回显错误代码
		IF (@RESULT_CODE != 0) GOTO ERROR

		--定义跟踪的事件
		DECLARE @ON BIT
		SET @ON = 1

		exec sp_trace_setevent @TraceID,17,1,@on
		exec sp_trace_setevent @TraceID,17,9,@on
		exec sp_trace_setevent @TraceID,17,6,@on
		exec sp_trace_setevent @TraceID,17,10,@on
		exec sp_trace_setevent @TraceID,17,14,@on
		exec sp_trace_setevent @TraceID,17,11,@on
		exec sp_trace_setevent @TraceID,17,35,@on
		exec sp_trace_setevent @TraceID,17,12,@on
		exec sp_trace_setevent @TraceID,10,15,@on
		exec sp_trace_setevent @TraceID,10,16,@on
		exec sp_trace_setevent @TraceID,10,1,@on
		exec sp_trace_setevent @TraceID,10,9,@on
		exec sp_trace_setevent @TraceID,10,17,@on
		exec sp_trace_setevent @TraceID,10,2,@on
		exec sp_trace_setevent @TraceID,10,10,@on
		exec sp_trace_setevent @TraceID,10,18,@on
		exec sp_trace_setevent @TraceID,10,11,@on
		exec sp_trace_setevent @TraceID,10,35,@on
		exec sp_trace_setevent @TraceID,10,12,@on
		exec sp_trace_setevent @TraceID,10,13,@on
		exec sp_trace_setevent @TraceID,10,6,@on
		exec sp_trace_setevent @TraceID,10,14,@on
		exec sp_trace_setevent @TraceID,12,15,@on
		exec sp_trace_setevent @TraceID,12,16,@on
		exec sp_trace_setevent @TraceID,12,1,@on
		exec sp_trace_setevent @TraceID,12,9,@on
		exec sp_trace_setevent @TraceID,12,17,@on
		exec sp_trace_setevent @TraceID,12,6,@on
		exec sp_trace_setevent @TraceID,12,10,@on
		exec sp_trace_setevent @TraceID,12,14,@on
		exec sp_trace_setevent @TraceID,12,18,@on
		exec sp_trace_setevent @TraceID,12,11,@on
		exec sp_trace_setevent @TraceID,12,35,@on
		exec sp_trace_setevent @TraceID,12,12,@on
		exec sp_trace_setevent @TraceID,12,13,@on
		exec sp_trace_setevent @TraceID,13,1,@on
		exec sp_trace_setevent @TraceID,13,9,@on
		exec sp_trace_setevent @TraceID,13,6,@on
		exec sp_trace_setevent @TraceID,13,10,@on
		exec sp_trace_setevent @TraceID,13,14,@on
		exec sp_trace_setevent @TraceID,13,11,@on
		exec sp_trace_setevent @TraceID,13,35,@on
		exec sp_trace_setevent @TraceID,13,12,@on

		--跟踪的列:
		--	TEXTDATA		与跟踪内捕获的事件类相关的文本值
		--	APPLICATIONNAME 创建与 SQL Server 实例的连接的客户端应用程序的名称
		--	NTUSERNAME		Microsoft Windows 用户名。
		--	LOGINNAME		客户端的 SQL Server 登录名
		--	DURATION		事件所花费的实耗时间(毫秒)
		--	STARTTIME		事件开始的时间(如果可用)
		--	ENDTIME			事件结束的时间
		--	READS			服务器代表事件所执行的逻辑磁盘读取次数
		--	WRITES			服务器代表事件所执行的物理磁盘写入次数
		--	CPU				事件所使用的 CPU 时间(微秒)
		--	SERVERNAME		被跟踪的 SQL Server 实例的名称
		--	ERROR			错误号
		--	OBJECTNAME		被访问的对象的名称
		--	DATABASENAME	语句中指定的数据库名称
		--	ROWCOUNTS		批处理中的行数

		--设置筛选器
		--TEXTDATA 不能为空
		exec sp_trace_setfilter @TraceID,1,0,1,NULL
		--排除SQL Server Profiler自身
		exec sp_trace_setfilter @TraceID,10,0,7,N'SQL Server Profiler%'
		--排除ApplicationName:Microsoft SQL Server Management Studio - 查询
		exec sp_trace_setfilter @TraceID,10,0,7,N'%Microsoft SQL Server Management Studio%'
		--排除ApplicationName:SQLAgent 作业
		exec sp_trace_setfilter @TraceID,10,0,7,N'SQLAgent%'
		exec sp_trace_setfilter @TraceID,10,0,7,N'SQLCMD'
		
		--LoginName不能为空
		exec sp_trace_setfilter @TraceID,11,0,1,NULL
		--排除复制/GCS变更类跟踪
		exec sp_trace_setfilter @TraceID,11,0,7,N'sa'
		exec sp_trace_setfilter @TraceID,11,0,7,N'distributor_admin'
		exec sp_trace_setfilter @TraceID,11,0,7,N'%\sqlserver'
		
		--Duration大于等于设定的值
		exec sp_trace_setfilter @TraceID,13,0,4,@FILTERDURATION
		--Duration不能为空
		exec sp_trace_setfilter @TraceID,13,0,1,NULL
		--CPU不能为空
		exec sp_trace_setfilter @TraceID,18,0,1,NULL
		--DatabaseName不能为空
		exec sp_trace_setfilter @TraceID,35,0,1,NULL
		--DatabaseName不能为系统库或者监控库
		exec sp_trace_setfilter @TraceID,35,0,1,N'master'
		exec sp_trace_setfilter @TraceID,35,0,1,N'temp'
		exec sp_trace_setfilter @TraceID,35,0,1,N'msdb'
		exec sp_trace_setfilter @TraceID,35,0,1,N'model'
		exec sp_trace_setfilter @TraceID,35,0,1,N'monitor'

		--启动跟踪
		EXEC SP_TRACE_SETSTATUS @TRACEID,1
		--存入新建的跟踪ID到DBO.TRACE_CURRENT_TRACEINFO,以便下次停用
		SET @TRACEFILE = @TRACEFILE+'.trc'

		INSERT INTO DBO.TRACE_CURRENT_TRACEINFO
		SELECT GETDATE(),@TRACEID,@TRACEFILE
		GOTO FINISH
		ERROR: 
			EXEC SP_TRACE_SETSTATUS @TRACEID,0
			EXEC SP_TRACE_SETSTATUS @TRACEID,2
			SELECT ERRORCODE=@RESULT_CODE
		FINISH: 
	END

	--导入跟踪数据
	IF LEN(@OLDTRACEFILE) > 1
	BEGIN
		INSERT INTO DBO.TRACE_TSQL(SQLTXT,SQLCHECKSUM,TEXTDATA,APPLICATIONNAME,NTUSERNAME,LOGINNAME,DURATION,STARTTIME,ENDTIME,READS,WRITES,CPU,SERVERNAME,ERROR,OBJECTID,OBJECTNAME,DATABASENAME,ROWCOUNTS)
			SELECT LEFT(REPLACE(CASE WHEN CHARINDEX('@',TEXTDATA) > 0 THEN SUBSTRING(TEXTDATA,CHARINDEX('EXEC ',TEXTDATA),CHARINDEX(' ',TEXTDATA,CHARINDEX('EXEC ',TEXTDATA)+5)-CHARINDEX('EXEC ',TEXTDATA)) ELSE CAST(SUBSTRING(TEXTDATA,1,4000) AS VARCHAR(4000)) END,'EXEC ',''),4000),
				CHECKSUM(REPLACE(CASE WHEN CHARINDEX('@',TEXTDATA) > 0 THEN SUBSTRING(TEXTDATA,CHARINDEX('EXEC ',TEXTDATA),CHARINDEX(' ',TEXTDATA,CHARINDEX('EXEC ',TEXTDATA)+5)-CHARINDEX('EXEC ',TEXTDATA)) ELSE CAST(SUBSTRING(TEXTDATA,1,8000) AS VARCHAR(8000)) END,'EXEC ','')),
				SUBSTRING(TEXTDATA,1,4000),APPLICATIONNAME,NTUSERNAME,LOGINNAME,DURATION,STARTTIME,ENDTIME,READS,WRITES,CPU,SERVERNAME,ERROR,OBJECTID,OBJECTNAME,DATABASENAME,ROWCOUNTS
			FROM FN_TRACE_GETTABLE(@OLDTRACEFILE,DEFAULT)
			WHERE TEXTDATA IS NOT NULL

		IF @DELETE_OLD_TRACE_FILE = 1
		BEGIN
			SET @CMD = 'DEL '+@OLDTRACEFILE
			EXEC XP_CMDSHELL @CMD,NO_OUTPUT
		END
	END
	
	--删除数据
	DELETE DBO.TRACE_TSQL WHERE STARTTIME < CONVERT(CHAR(8),GETDATE()-@KEEPDATADAYS,112)
END


GO

/****** Object:  StoredProcedure [dbo].[JOB_UPDATESTATS]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO




CREATE PROCEDURE [dbo].[JOB_UPDATESTATS]
AS
BEGIN

	SET NOCOUNT ON
	DECLARE @SQL VARCHAR(MAX)

	IF NOT EXISTS(SELECT 1 FROM APP_SETTING WHERE UPDATESTATS=1)
		return

	SELECT @SQL = ISNULL(@SQL+'','')+'EXEC ['+name+'].dbo.SP_UPDATESTATS;'
	FROM MASTER.SYS.DATABASES
	WHERE DATABASE_ID > 4 
		AND STATE = 0
		AND IS_READ_ONLY = 0
		AND IS_DISTRIBUTOR = 0
		AND recovery_model=1
		AND NAME <> 'MONITOR'
	EXEC(@SQL)

END


GO

/****** Object:  StoredProcedure [dbo].[mssql_exporter]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



CREATE PROCEDURE [dbo].[mssql_exporter]
AS
BEGIN

--type 0 Performance indicators do not require calculation of differences
--type 1 Performance indicators require calculation of differences
--type 2 Performance indicators are calculated in a special way
--type 3 Belongs to the alarm indicator type

IF OBJECT_ID('TEMPDB.DBO.#tmp_mssql_exporter','U') IS NOT NULL
	DROP TABLE #tmp_mssql_exporter
create table #tmp_mssql_exporter(metrics_name varchar(200),counter_value varchar(100),counter_name varchar(100),type tinyint)

insert into #tmp_mssql_exporter
select i.COUNTER_SHORT_NAME,p.cntr_value,i.COUNTER_NAME,i.COMPUTE_INTERVAL 
from Monitor.DBO.MONITOR_INSANCE_COUNTER(nolock) i 
left join master.sys.DM_OS_PERFORMANCE_COUNTERS(nolock) p 
on i.[OBJECT_NAME]=p.[object_name] and i.COUNTER_NAME=p.counter_name and i.INSTANCE_NAME=p.instance_name

/*
insert into #tmp_mssql_exporter
select 'mssql_version',substring(@@version,0,charindex('(',@@version)),'version',2

insert into #tmp_mssql_exporter
select 'mssql_collation',convert(varchar(100),serverproperty(N'Collation')),'collation',2

insert into #tmp_mssql_exporter
select 'mssql_sqlserver_start_time',convert(varchar(20),sqlserver_start_time,120),'sqlserver_start_time',2 from master.sys.dm_os_sys_info
*/

declare @total_cpu_count int,@use_cpu_count int
select @total_cpu_count=cpu_count from master.sys.dm_os_sys_info

SELECT @use_cpu_count=COUNT(*)
FROM sys.dm_os_schedulers
WHERE is_online = 1
  AND status = 'VISIBLE ONLINE' 

insert into #tmp_mssql_exporter
select 'mssql_virtual_total_cpu',@total_cpu_count,'virtual_total_cpu',2

insert into #tmp_mssql_exporter
SELECT 'mssql_virtual_free_cpu',@total_cpu_count-@use_cpu_count,'virtual_free_cpu',2
  
insert into #tmp_mssql_exporter
select 'mssql_virtual_total_memory',convert(bigint,round(total_physical_memory_kb*1.00/1024/1024,0)),'virtual_total_memory',2 from sys.dm_os_sys_memory

insert into #tmp_mssql_exporter
select 'mssql_virtual_free_memory',convert(bigint,round(available_physical_memory_kb*1.00/1024/1024,0)),'virtual_free_memory',2 from sys.dm_os_sys_memory

insert into #tmp_mssql_exporter
SELECT 'mssql_cpu_use_precent',(100 - record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]','int')) as cpu_use_precent,'cpu_use_precent',2
FROM ( SELECT top 1 timestamp ,CONVERT(XML, record) AS record
FROM master.sys.dm_os_ring_buffers
WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
AND record LIKE '%<SystemHealth>%'
ORDER BY timestamp desc
) AS x

insert into #tmp_mssql_exporter
SELECT 'mssql_slow_queries',COUNT(1) as mssql_slow_query,'slow_queries',2
FROM MONITOR.DBO.TRACE_TSQL
WHERE STARTTIME >= DATEADD(MI,-1,GETDATE()) and STARTTIME<= getdate()

insert into #tmp_mssql_exporter
SELECT 'mssql_disk_iops',CAST(ISNULL(SUM(ISNULL(CAST(NUM_OF_READS AS BIGINT),0)+ISNULL(NUM_OF_WRITES ,0)),0) AS NUMERIC(18,1)),'iops',2
FROM SYS.DM_IO_VIRTUAL_FILE_STATS(NULL,NULL)

insert into #tmp_mssql_exporter
SELECT 'mssql_num_of_writes',ISNULL(SUM(CAST(NUM_OF_WRITES AS BIGINT)),0),'num_of_writes',2
FROM SYS.DM_IO_VIRTUAL_FILE_STATS(NULL,NULL)
UNION ALL
SELECT 'mssql_num_of_reads',ISNULL(SUM(CAST(NUM_OF_READS AS BIGINT)),0),'num_of_reads',2
FROM SYS.DM_IO_VIRTUAL_FILE_STATS(NULL,NULL) 
UNION ALL
SELECT 'mssql_io_stall_read_ms',max(io_stall_read_ms),'io_stall_read_ms',2
FROM SYS.DM_IO_VIRTUAL_FILE_STATS(NULL,NULL)
UNION ALL
SELECT 'mssql_io_stall_write_ms',max(io_stall_write_ms),'io_stall_write_ms',2
FROM SYS.DM_IO_VIRTUAL_FILE_STATS(NULL,NULL) 

;WITH T_SESSION AS
(
	SELECT SESSION_ID
	FROM SYS.DM_EXEC_SESSIONS(NOLOCK)
	WHERE IS_USER_PROCESS = 1
	AND STATUS NOT IN ('PRECONNECT','DORMANT')
	AND LOGIN_NAME NOT IN('sa','monitor') AND LOGIN_NAME NOT LIKE '%\%'
)
insert into #tmp_mssql_exporter
SELECT 'mssql_in_flow',CAST(ISNULL(SUM(ISNULL(CAST(A.NET_PACKET_SIZE AS BIGINT),0)*ISNULL(A.NUM_READS,0))/1024.0,0) AS NUMERIC(18,1)),'in_flow',2
FROM SYS.DM_EXEC_CONNECTIONS(NOLOCK) A,T_SESSION B
WHERE A.SESSION_ID = B.SESSION_ID
UNION ALL
SELECT 'mssql_out_flow',CAST(ISNULL(SUM(ISNULL(CAST(A.NET_PACKET_SIZE AS BIGINT),0)*ISNULL(A.NUM_WRITES,0))/1024.0,0) AS NUMERIC(18,1)),'out_flow',2
FROM SYS.DM_EXEC_CONNECTIONS(NOLOCK) A,T_SESSION B
WHERE A.SESSION_ID = B.SESSION_ID

insert into #tmp_mssql_exporter
SELECT 'mssql_database_mdfsize',CAST(ISNULL((case when SUM(CAST(SIZE AS BIGINT)*8.0)=0 then 0 when SUM(CAST(SIZE AS BIGINT)*8.0)<1048576 then 1048576 else SUM(CAST(SIZE AS BIGINT)*8.0) end)/1024/1024,0) AS NUMERIC(18,1)),'database_mdfsize',2
FROM SYS.DATABASES A(NOLOCK),SYS.MASTER_FILES B(NOLOCK) 
WHERE A.DATABASE_ID = B.DATABASE_ID AND B.type=0
UNION ALL
SELECT 'mssql_database_ldfsize',CAST(ISNULL((case when SUM(CAST(SIZE AS BIGINT)*8.0)=0 then 0 when SUM(CAST(SIZE AS BIGINT)*8.0)<1048576 then 1048576 else SUM(CAST(SIZE AS BIGINT)*8.0) end)/1024/1024,0) AS NUMERIC(18,1)),'database_ldfsize',2
FROM SYS.DATABASES A(NOLOCK),SYS.MASTER_FILES B(NOLOCK)
WHERE A.DATABASE_ID = B.DATABASE_ID AND B.type=1


IF OBJECT_ID('TEMPDB.DBO.#DatabaseFile','U') IS NOT NULL
	DROP TABLE #DatabaseFile

CREATE TABLE #DatabaseFile (  
database_id INT
,name SYSNAME
, size INT  
, unused_space INT    
);  

declare @version bigint
set @version=convert(bigint,DATABASEPROPERTYEX('master','version'))

/*
IF @version>661
BEGIN
	EXEC sp_MSforeachdb '  
	USE [?];  
	  
	INSERT #DatabaseFile (database_id,name,size, unused_space)  
	SELECT db_id() AS database_id,df.name,CONVERT(BIGINT, df.size) * 8 / 1024, r.unused_space   
	FROM (select * from sys.database_files where type=0 and name not in(''moniotr'')) AS df  
	LEFT JOIN (  
	SELECT database_id, file_id, unallocated_extent_page_count * 8 / 1024 AS unused_space  
	FROM sys.dm_db_file_space_usage
	) AS r  
	ON df.file_id = r.file_id 
	;';  

	insert into #tmp_mssql_exporter
	select 'mssql_database_usesize',max(convert(int,convert(decimal(10,2),unused_space*1.00/size)*100)),'database_usesize',2 from #DatabaseFile where name not in('master','Monitor','MSDBData')
END
*/

IF OBJECT_ID('TEMPDB.DBO.#DISKFREE','U') IS NOT NULL
	DROP TABLE #DISKFREE
CREATE TABLE #DISKFREE(LABEL VARCHAR(100) NOT NULL,FREEMB INT NOT NULL)
INSERT INTO #DISKFREE EXEC MASTER.DBO.XP_FIXEDDRIVES

IF NOT EXISTS(SELECT 1 FROM #DISKFREE)
BEGIN
insert into #tmp_mssql_exporter
SELECT 'mssql_systemdisk_free',70,'system_free',2
union all
SELECT 'mssql_backupdisk_free',999,'backup_free',2
union all
SELECT 'mssql_datadisk_free',999,'Minimum disk remaining capacity',2
END
ELSE
BEGIN
insert into #tmp_mssql_exporter
SELECT 'mssql_systemdisk_free',isnull(SUM(freemb)/1024,0),'system_free',2 FROM #DISKFREE WHERE LABEL='C'
union all
SELECT 'mssql_backupdisk_free',isnull(SUM(freemb)/1024,999),'backup_free',2 FROM #DISKFREE WHERE LABEL='E'
union all
SELECT 'mssql_datadisk_free',isnull(SUM(freemb)/1024,0),'Minimum disk remaining capacity',2 FROM #DISKFREE WHERE LABEL not in('C','E')
END

insert into #tmp_mssql_exporter
SELECT 'mssql_full_backup_fail',count(1),'full_backup_fail',3
FROM MONITOR.DBO.BACKUP_TRACE(NOLOCK)
WHERE TYPE = 1
AND SUCCESS = 0
AND WRITETIME >= DATEADD(MI,-1,GETDATE()) and WRITETIME<getdate()
UNION ALL 
SELECT 'mssql_log_backup_fail',count(1),'log_backup_fail',3
FROM MONITOR.DBO.BACKUP_TRACE(NOLOCK)
WHERE TYPE = 2
AND SUCCESS = 0
AND WRITETIME >= DATEADD(MI,-1,GETDATE()) and WRITETIME<getdate()

insert into #tmp_mssql_exporter
SELECT 'mssql_job_fail',count(1),'job_fail',3
FROM MSDB.DBO.SYSJOBHISTORY A,MSDB.DBO.SYSJOBS B
WHERE A.JOB_ID = B.JOB_ID
AND A.RUN_DATE = CONVERT(CHAR(8),GETDATE(),112)
AND RIGHT('000000'+LTRIM(A.RUN_TIME),6) >= LEFT(REPLACE(CONVERT(CHAR(30),DATEADD(MI,-1,GETDATE()),114),':',''),LEN(REPLACE(CONVERT(CHAR(30),DATEADD(MI,-1,GETDATE()),114),':',''))-3)
AND A.RUN_STATUS = 0 AND EXISTS(select 1 from master.sys.database_mirroring where mirroring_guid is not null and mirroring_role=1)

insert into #tmp_mssql_exporter
SELECT 'mssql_snapshot_deploy',count(1),'snapshot_deploy',3
FROM SYS.DATABASE_MIRRORING A LEFT JOIN SYS.DATABASES B
ON DB_NAME(A.DATABASE_ID)+'_DR' = B.NAME
AND B.IS_READ_ONLY = 1
WHERE A.MIRRORING_STATE = 4
AND A.MIRRORING_ROLE = 2
AND (B.NAME IS NULL
OR B.STATE = 4)

DECLARE @SQL varchar(1000)
IF OBJECT_ID('TEMPDB.DBO.#tmp_is_alwayson','U') IS NOT NULL
	DROP TABLE #tmp_is_alwayson
CREATE TABLE #tmp_is_alwayson (  
cnt int  
)

IF OBJECT_ID('TEMPDB.DBO.#tmp111','U') IS NOT NULL
	DROP TABLE #tmp111
CREATE TABLE #tmp111 (  
cnt int  
)

set @version=convert(bigint,DATABASEPROPERTYEX('master','version'))
IF @version>=869
BEGIN
	delete from #tmp111
	
	SET @SQL= '
	IF EXISTS(SELECT 1 FROM sys.availability_groups)
		insert into #tmp_is_alwayson values(1)
	'
	EXEC(@SQL)

	IF EXISTS(SELECT 1 FROM #tmp_is_alwayson)
	BEGIN
		SET @SQL= '
		if exists(select 1 from master.sys.databases where database_id>4 and name not in(''monitor''))
		begin
			if exists(select 1 from sys.dm_hadr_availability_replica_states where is_local=0 and connected_state=0)
			begin
				insert into #tmp111
				values(99999)
			end
			else if exists(select 1 from sys.dm_hadr_database_replica_states where is_local=0 and synchronization_state=0)
			begin
				insert into #tmp111
				values(99999)
			end
			else
			begin
				insert into #tmp111
				select sum(isnull(secondary_lag_seconds,99999)) from sys.dm_hadr_database_replica_states where is_local=0
			end
		end
		else
		begin
			insert into #tmp111
			values(0)
		end
		;';
		EXEC(@SQL)

		insert into #tmp_mssql_exporter
		select 'mssql_alwayson_delay',isnull(sum(cnt),0),'alwayson_delay',2 from #tmp111

		delete from #tmp111

		SET @SQL= '
		insert into #tmp111
		SELECT count(1)
		FROM master.sys.databases 
		where database_id>4 and name not in(''monitor'') and replica_id is null and state=0 and is_read_only=0 and recovery_model=1 and name NOT IN(SELECT NAME FROM MONITOR.DBO.MIRRORING_FILTER(NOLOCK))
		'
		EXEC(@SQL)

		insert into #tmp_mssql_exporter
		select 'mssql_alwayson_deploy',isnull(sum(cnt),0),'alwayson_deploy',3 from #tmp111

		delete from #tmp111

		SET @SQL= '
		insert into #tmp111
		SELECT count(1)
		FROM sys.dm_hadr_database_replica_states 
		WHERE synchronization_state not in(2)
		'
		EXEC(@SQL)

		insert into #tmp_mssql_exporter
		select 'mssql_alwayson_status',isnull(sum(cnt),0),'mssql_alwayson_status',3 from #tmp111

	END
END

IF EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING WHERE mirroring_role=1)
BEGIN
	insert into #tmp_mssql_exporter
	SELECT 'mssql_mirroring_delay',isnull(sum(cntr_value),0),'mirroring_delay',2 FROM master.sys.dm_os_performance_counters 
	WHERE object_name LIKE '%Database Mirroring%' 
	AND counter_name='Log Send Queue KB' 

	insert into #tmp_mssql_exporter
	SELECT 'mssql_mirroring_deploy',count(1),'mirroring_deploy',3
	FROM master.sys.DATABASES A LEFT JOIN SYS.DATABASE_MIRRORING B
	ON A.DATABASE_ID = B.DATABASE_ID
	WHERE A.DATABASE_ID > 4
	AND A.IS_READ_ONLY = 0
	AND A.IS_DISTRIBUTOR = 0
	AND A.STATE = 0
	AND B.MIRRORING_STATE IS NULL
	AND A.recovery_model=1
	AND A.name not in('monitor')
	AND A.name not in(select name from monitor.dbo.MIRRORING_FILTER)

	insert into #tmp_mssql_exporter
	SELECT 'mssql_mirroring_status',count(1),'mirroring_status',3
	FROM SYS.DATABASE_MIRRORING
	WHERE mirroring_role=1 and ISNULL(MIRRORING_STATE,4) NOT IN (2,4)
END

insert into #tmp_mssql_exporter
select 'mssql_serveice_available',0,'mssql_serveice_available',3

select * from #tmp_mssql_exporter order by type

END



GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_DrToDb]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_DrToDb]
AS

/**
功能：DB故障进行验证和切换到DR
验证方式：
1.判断DR镜像状态，状态为断开可进行切换
2.判断GameDB故障时间，小于10分钟可进行切换
3.判断DR落后DB时间,[待发送日志]小于10秒(10M)为可进行切换
4.判断DR跟进DB情况,[待重做日志]小于1M为可进行切换
切换方式：
Use master  alter database test set partner FORCE_SERVICE_ALLOW_DATA_LOSS;
检测镜像是否都切换为主

exec monitor.dbo.Sys_AutoSwitch_DrToDb

**/

declare @msg varchar(1000)

declare @r int,@strsql varchar(max) ,@dbname varchar(100)  
DECLARE @ERR_FAILURE INT = 1                               
set @dbname=''    

BEGIN TRY
	declare @version bigint,@is_alwayson_flag tinyint
	set @version=convert(bigint,DATABASEPROPERTYEX('master','version'))
	set @is_alwayson_flag=0
	
	IF OBJECT_ID('TEMPDB.DBO.#tmp_dblist','U') IS NOT NULL
		DROP TABLE #tmp_dblist
	create table #tmp_dblist(name varchar(200))
	
	IF @version>=869
		exec('insert into #tmp_dblist select name from sys.availability_groups')
	
	IF exists(select 1 from #tmp_dblist)
		set @is_alwayson_flag=1

	IF not exists(select database_id from master.sys.database_mirroring where mirroring_guid is not null) and not exists(select 1 from #tmp_dblist)
	BEGIN
		set @msg='alwayson/mirroring is not exists'
		select -1 as status,@msg as msg
		return -1
	END		
	
	DECLARE @SQL VARCHAR(MAX)
	DECLARE @i INT
	IF @is_alwayson_flag=1
	BEGIN
		IF OBJECT_ID('TEMPDB.DBO.#repl_state','U') IS NOT NULL
			DROP TABLE #repl_state
		CREATE TABLE #repl_state(is_local bit,role tinyint,connected_state tinyint,synchronization_health tinyint,operational_state tinyint,recovery_health tinyint,last_connect_error_number int,last_connect_error_timestamp datetime)
		
		SET @i=1
		WHILE @i<=60
		BEGIN
			if @i<>1
				waitfor delay '00:00:01'

			SET @SQL='delete from #repl_state;insert into #repl_state select is_local,role,connected_state,synchronization_health,operational_state,recovery_health,last_connect_error_number,last_connect_error_timestamp from master.sys.dm_hadr_availability_replica_states where is_local=1 and role=2'
			EXEC(@SQL)

			IF EXISTS(SELECT 1 FROM #repl_state WHERE connected_state=0)
				SET @i=60
			
			SET @i=@i+1
		END
		
		IF NOT EXISTS(SELECT 1 FROM #repl_state WHERE connected_state=0)
		BEGIN
			set @msg='GameDB state has been disconnected'
			select -1 as status,@msg as msg
			return -1
		END
		ELSE
		BEGIN
			SET @SQL='
			DECLARE @SQL varchar(max),@group_name varchar(1000),@msg VARCHAR(100)
			IF EXISTS(SELECT 1 FROM sys.availability_groups)
			BEGIN
				BEGIN TRY
					select @group_name=name from sys.availability_groups
					SET @SQL=''USE MASTER ALTER AVAILABILITY GROUP [''+@group_name+''] FORCE_FAILOVER_ALLOW_DATA_LOSS''
					EXEC(@SQL)
				END TRY
				BEGIN CATCH
					SET @msg=''GameDr switch err''
				END CATCH
			END
			'
			--PRINT(@SQL)
			BEGIN TRY
				EXEC(@SQL)
			END TRY
			BEGIN CATCH	
				SET @msg='GameDr switch failed'
			END CATCH

			SET @i=1
			WHILE @i<=60
			BEGIN
				if @i<>1
					waitfor delay '00:00:01'

				SET @SQL='delete from #repl_state;insert into #repl_state select is_local,role,connected_state,synchronization_health,operational_state,recovery_health,last_connect_error_number,last_connect_error_timestamp from master.sys.dm_hadr_availability_replica_states where is_local=1 and role=1'
				EXEC(@SQL)

				IF EXISTS(SELECT 1 FROM #repl_state)
					SET @i=60
			
				SET @i=@i+1
			END

			IF exists(select 1 from #repl_state where is_local=1 and role=1)
			BEGIN
				set @msg='GameDR switch Success'
				select 1 as status,@msg as msg
				return 1
			END
			ELSE
			BEGIN
				set @msg='GameDr switch Failed'
				select -1 as status,@msg as msg
				return -1
			END
		END
	END
	ELSE
	BEGIN
		--判断DR镜像状态，状态为断开可进行切换
		if not exists(select 1 from master.sys.database_mirroring
		where mirroring_state=1)
		begin
			set @msg='GameDB state has been disconnected'
			select -1 as status,@msg as msg
			return -1
		end

		--判断DB待未发送日志量大于10M，不允许切换
		IF exists(SELECT 1 FROM master.sys.dm_os_performance_counters 
		WHERE object_name LIKE '%Database Mirroring%' 
		AND counter_name='Log Send Queue KB' and cntr_value>102400) --100M
		begin
			set @msg='GameDB to send log exceeds 100M'
			select -1 as status,@msg as msg
			return -1
		end

		--判断DR待还原日志量大于100M，不允许切换
		IF exists(SELECT 1 FROM master.sys.dm_os_performance_counters 
		WHERE object_name LIKE '%Database Mirroring%' 
		AND counter_name='Redo Queue KB' and cntr_value>102400) --100M
		begin
			set @msg='GameDB to redo log exceeds 1M'
			select -1 as status,@msg as msg
			return -1
		end

		--获取待切换镜像DB列表
		DECLARE dblist_cur cursor static forward_only Read_only for 
		select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
		on a.dbid=b.database_id 
		where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=2 and b.mirroring_state=1
		OPEN dblist_cur;

		FETCH NEXT FROM dblist_cur INTO @dbname
		WHILE @@FETCH_STATUS = 0
		BEGIN
				--强制故障切换
				set @strsql='Use master  alter database '+@dbname+' set partner FORCE_SERVICE_ALLOW_DATA_LOSS;'
				exec(@strsql)
				if @@error>0
				begin
					set @msg='GameDR switch abnormal failure'
					select -1 as status,@msg as msg
					return -1
				end

				FETCH NEXT FROM dblist_cur INTO @dbname;
		END
		CLOSE dblist_cur;
		DEALLOCATE dblist_cur;

		--检测镜像是否都切换为主
		if exists(select 1 from master.sys.database_mirroring
		where mirroring_role=2)
		begin
			set @msg='GameDr has no DB switching'
			select -1 as status,@msg as msg
			return -1
		end

		set @msg='GameDR switch Success'
		select 1 as status,@msg as msg

		RETURN 1
	END

END TRY
BEGIN CATCH
	--扑捉异常错误
	set @msg='GameDr execution exception'
	select -1 as status,@msg as msg
	
	RETURN	-1
	
END CATCH


GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_FailOver]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_FailOver]
(@msg varchar(1000) output)
AS


declare @strsql varchar(max) ,@dbname varchar(100)                              
set @dbname=''

BEGIN TRY

	--判断DR镜像状态，状态为断开可进行切换
	if not exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1 and mirroring_state=4)
	begin
		set @msg='GameDB state has been Synchronized'
		return -1
	end

	--获取待切换镜像DB列表
	DECLARE dblist_cur cursor static forward_only Read_only for 
	select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
	on a.dbid=b.database_id 
	where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=1 and b.mirroring_state=4
	OPEN dblist_cur;

	FETCH NEXT FROM dblist_cur INTO @dbname
	WHILE @@FETCH_STATUS = 0
	BEGIN
			--强制故障切换
			set @strsql='Use master  alter database '+@dbname+' set partner safety full;'
			set @strsql=@strsql+'WAITFOR DELAY ''00:00:10'';'
			set @strsql=@strsql+'alter database '+@dbname+' set partner failover;'
			
			exec(@strsql)
			if @@error>0
			begin
				set @msg='GameDR switch abnormal failure'
				return -1
			end

			FETCH NEXT FROM dblist_cur INTO @dbname;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	--检测镜像是否都切换为主
	if exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1)
	begin
		set @msg='GameDr has no DB switching'
		return -1
	end

	set @msg='GameDR switch Success'

	RETURN 1

END TRY
BEGIN CATCH
	--扑捉异常错误
	--set @msg='GameDb execution exception'
	set @msg=ERROR_MESSAGE()
	RETURN	-1
	
END CATCH


GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_LossOver]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_LossOver]
(@msg varchar(1000) output)
AS

declare @strsql varchar(max) ,@dbname varchar(100)                              
set @dbname=''

BEGIN TRY

	--判断DR镜像状态，状态为断开可进行切换
	if not exists(select 1 from master.sys.database_mirroring
	where mirroring_role=2 and mirroring_state=1)
	begin
		set @msg='GameDB state has been Suspended'
		return -1
	end

	--判断DR落后DB时间,[待发送日志]小于10秒(10M)为可进行切换
	IF exists(SELECT 1 FROM master.sys.dm_os_performance_counters 
	WHERE object_name LIKE '%Database Mirroring%' 
	AND counter_name='Log Send Queue KB' and cntr_value>10240) --10M
	begin
		set @msg='GameDB to send log exceeds 10M'
		return -1
	end

	--判断DR跟进DB情况,[待重做日志]小于1M为可进行切换
	IF exists(SELECT 1 FROM master.sys.dm_os_performance_counters 
	WHERE object_name LIKE '%Database Mirroring%' 
	AND counter_name='Redo Queue KB' and cntr_value>1024) --1M
	begin
		set @msg='GameDB to redo log exceeds 1M'
		return -1
	end

	--获取待切换镜像DB列表
	DECLARE dblist_cur cursor static forward_only Read_only for 
	select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
	on a.dbid=b.database_id 
	where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=2 and b.mirroring_state=1
	OPEN dblist_cur;

	FETCH NEXT FROM dblist_cur INTO @dbname
	WHILE @@FETCH_STATUS = 0
	BEGIN
			--强制故障切换
			set @strsql='Use master  alter database '+@dbname+' set partner FORCE_SERVICE_ALLOW_DATA_LOSS;'
			
			exec(@strsql)
			if @@error>0
			begin
				set @msg='GameDR switch abnormal failure'
				return -1
			end

			FETCH NEXT FROM dblist_cur INTO @dbname;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	--检测镜像是否都切换为主
	if exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1)
	begin
		set @msg='GameDr has no DB switching'
		return -1
	end

	set @msg='GameDR switch Success'

	RETURN 1

END TRY
BEGIN CATCH
	--扑捉异常错误
	set @msg='GameDr execution exception'
	
	RETURN	-1
	
END CATCH


GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_Remove]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_Remove]
(@msg varchar(1000) output)
AS

declare @strsql varchar(max) ,@dbname varchar(100)                              
set @dbname=''    

BEGIN TRY

	--判断DB镜像状态，状态为Suspended可进行Resume
	if not exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1)
	begin
		set @msg='GameDB Is Not Principal'
		return -1
	end

	--获取待Resume镜像DB列表
	DECLARE dblist_cur cursor static forward_only Read_only for 
	select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
	on a.dbid=b.database_id 
	where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=1 
	OPEN dblist_cur;

	FETCH NEXT FROM dblist_cur INTO @dbname
	WHILE @@FETCH_STATUS = 0
	BEGIN
			--resume
			set @strsql='Use master  alter database '+@dbname+' set partner off;'
			exec(@strsql)
			if @@error>0
			begin
				set @msg='GameDb Remove abnormal failure'
				return -1
			end

			FETCH NEXT FROM dblist_cur INTO @dbname;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	--检测镜像是否Resume
	if exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1)
	begin
		set @msg='GameDb has no Remove'
		return -1
	end

	set @msg='GameDb Remove Success'

	RETURN 1

END TRY
BEGIN CATCH
	--扑捉异常错误
	set @msg='GameDb execution exception'
	
	RETURN	-1
	
END CATCH


GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_Resume]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_Resume]
(@msg varchar(1000) output)
AS

declare @strsql varchar(max) ,@dbname varchar(100)                              
set @dbname=''    

BEGIN TRY

	--判断DB镜像状态，状态为Suspended可进行Resume
	if not exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1 and mirroring_state=0)
	begin
		set @msg='GameDB state has been Suspended'
		return -1
	end

	--获取待Resume镜像DB列表
	DECLARE dblist_cur cursor static forward_only Read_only for 
	select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
	on a.dbid=b.database_id 
	where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=1 and b.mirroring_state=0
	OPEN dblist_cur;

	FETCH NEXT FROM dblist_cur INTO @dbname
	WHILE @@FETCH_STATUS = 0
	BEGIN
			--resume
			set @strsql='Use master  alter database '+@dbname+' set partner resume;'
			exec(@strsql)
			if @@error>0
			begin
				set @msg='GameDb Resume abnormal failure'
				return -1
			end

			FETCH NEXT FROM dblist_cur INTO @dbname;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	--检测镜像是否Resume
	if exists(select 1 from master.sys.database_mirroring
	where mirroring_state=0)
	begin
		set @msg='GameDb has no Synchronized'
		return -1
	end

	set @msg='GameDb Resume Success'

	RETURN 1

END TRY
BEGIN CATCH
	--扑捉异常错误
	set @msg='GameDb execution exception'
	
	RETURN	-1
	
END CATCH


GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_SafetyOff]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_SafetyOff]
(@msg varchar(1000) output)
AS

declare @strsql varchar(max) ,@dbname varchar(100)                              
set @dbname=''    

BEGIN TRY

	--判断DB镜像状态，状态为Principal可进行SafetyOff
	if not exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1)
	begin
		set @msg='GameDB Is not Principal'
		return -1
	end

	--获取待Resume镜像DB列表
	DECLARE dblist_cur cursor static forward_only Read_only for 
	select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
	on a.dbid=b.database_id 
	where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=1 
	OPEN dblist_cur;

	FETCH NEXT FROM dblist_cur INTO @dbname
	WHILE @@FETCH_STATUS = 0
	BEGIN
			--resume
			set @strsql='Use master  alter database '+@dbname+' set partner safety off;'
			exec(@strsql)
			if @@error>0
			begin
				set @msg='GameDb SafetyOff abnormal failure'
				return -1
			end

			FETCH NEXT FROM dblist_cur INTO @dbname;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	--检测镜像是否Resume
	if exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1 and mirroring_safety_level=2)
	begin
		set @msg='GameDb has no SafetyOff'
		return -1
	end

	set @msg='GameDb SafetyOff Success'

	RETURN 1

END TRY
BEGIN CATCH
	--扑捉异常错误
	set @msg='GameDb execution exception'
	
	RETURN	-1
	
END CATCH


GO

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_Suspend]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE Proc [dbo].[Sys_AutoSwitch_Suspend]
(@msg varchar(1000) output)
AS

declare @strsql varchar(max) ,@dbname varchar(100)                              
set @dbname=''    

BEGIN TRY

	--判断DB镜像状态，状态为Suspended可进行Suspend
	if not exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1 and mirroring_state=4)
	begin
		set @msg='GameDB Is not Synchronized'
		return -1
	end

	--获取待Resume镜像DB列表
	DECLARE dblist_cur cursor static forward_only Read_only for 
	select name from master.sys.sysdatabases  a left join master.sys.database_mirroring b
	on a.dbid=b.database_id 
	where dbid>4 and name not in('monitor') and b.mirroring_guid is not null and b.mirroring_role=1 
	OPEN dblist_cur;

	FETCH NEXT FROM dblist_cur INTO @dbname
	WHILE @@FETCH_STATUS = 0
	BEGIN
			--resume
			set @strsql='Use master  alter database '+@dbname+' set partner Suspend;'
			exec(@strsql)
			if @@error>0
			begin
				set @msg='GameDb Suspend abnormal failure'
				return -1
			end

			FETCH NEXT FROM dblist_cur INTO @dbname;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	--检测镜像是否Resume
	if exists(select 1 from master.sys.database_mirroring
	where mirroring_role=1 and mirroring_state=4)
	begin
		set @msg='GameDb has no Suspend'
		return -1
	end

	set @msg='GameDb Suspend Success'

	RETURN 1

END TRY
BEGIN CATCH
	--扑捉异常错误
	--set @msg='GameDb execution exception'
	set @msg=ERROR_MESSAGE()
	RETURN	-1
	
END CATCH


GO

USE [Monitor]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



CREATE PROCEDURE [dbo].[TOOL_BACKUP_DATABASE]
	@TYPE [int] = 1,
	@BACKUP_ID varchar(100) = '',
	@TARGETDBNAME [varchar](max) = '%',
	@BACKUP_PATH [varchar](max) = '',
	@BACKUP_FILETAG [varchar](max) = ''
AS
BEGIN
	SET NOCOUNT ON;
	DECLARE @DISK_MIN_SIZE_MB INT = 10240
	DECLARE @KEEP_BACKUP_DAYS INT
	DECLARE @CHECKER INT = 0
	DECLARE @SUCCESS INT = 0
	DECLARE @CMD VARCHAR(8000)
	DECLARE @SUFFIX VARCHAR(10) = '.bak'

	DECLARE @SQL NVARCHAR(MAX),@FETCH_STATUS INT
	
	DECLARE	@APP VARCHAR(100),
		@FULL_BACKUP_PATH VARCHAR(100),
		@LOG_BACKUP_PATH VARCHAR(100),
		@KEEP_FULL_BACKUP_DAYS INT,
		@KEEP_LOG_BACKUP_DAYS INT,
		@FULL_BACKUP_MIN_SIZE_MB INT,
		@LOG_BACKUP_MIN_SIZE_MB INT,
		@CLUSTER_ID VARCHAR(100),
		@CLUSTER_DOMAIN VARCHAR(100),
		@IP VARCHAR(100),
		@PORT VARCHAR(100),
		@ROLE VARCHAR(100),
		@MASTER_IP VARCHAR(100),
		@MASTER_PORT VARCHAR(100),
		@SYNCHRONOUS_MODE VARCHAR(100),
		@BK_BIZ_ID VARCHAR(100),
		@BK_CLOUD_ID VARCHAR(100),
		@VERSION VARCHAR(100),
		@BACKUP_TYPE VARCHAR(100),
		@DATA_SCHEMA_GRANT VARCHAR(100),
		@TIME_ZONE VARCHAR(100),
		@CHARSET VARCHAR(100),
		@BACKUP_CLIENT_PATH VARCHAR(1000),
		@BACKUP_STORAGE_TYPE VARCHAR(100),
		@FULL_BACKUP_REPORT_PATH VARCHAR(1000),
		@LOG_BACKUP_REPORT_PATH VARCHAR(1000),
		@FULL_BACKUP_FILETAG VARCHAR(100),
		@LOG_BACKUP_FILETAG VARCHAR(100),
		@SHRINK_SIZE BIGINT,
		@ERROR_MESSAGE VARCHAR(4000)

	IF @BACKUP_ID=''
	BEGIN
		SET @BACKUP_ID=CONVERT(VARCHAR(36),NEWID())
	END
	

	--获取备份配置数据
	SELECT @APP = APP,
		@FULL_BACKUP_PATH = FULL_BACKUP_PATH,
		@LOG_BACKUP_PATH = LOG_BACKUP_PATH,
		@KEEP_FULL_BACKUP_DAYS = KEEP_FULL_BACKUP_DAYS,
		@KEEP_LOG_BACKUP_DAYS = KEEP_LOG_BACKUP_DAYS,
		@FULL_BACKUP_MIN_SIZE_MB = FULL_BACKUP_MIN_SIZE_MB,
		@LOG_BACKUP_MIN_SIZE_MB = LOG_BACKUP_MIN_SIZE_MB,
		@CLUSTER_ID=CLUSTER_ID,
		@CLUSTER_DOMAIN=CLUSTER_DOMAIN,
		@IP=IP,
		@PORT=PORT,
		@ROLE=ROLE,
		@MASTER_IP=MASTER_IP,
		@MASTER_PORT=MASTER_PORT,
		@SYNCHRONOUS_MODE=SYNCHRONOUS_MODE,
		@BK_BIZ_ID=BK_BIZ_ID,
		@BK_CLOUD_ID=BK_CLOUD_ID,
		@VERSION=VERSION,
		@BACKUP_TYPE=BACKUP_TYPE,
		@DATA_SCHEMA_GRANT=DATA_SCHEMA_GRANT,
		@TIME_ZONE=TIME_ZONE,
		@CHARSET=CHARSET,
		@BACKUP_CLIENT_PATH=BACKUP_CLIENT_PATH,
		@BACKUP_STORAGE_TYPE=BACKUP_STORAGE_TYPE,
		@FULL_BACKUP_REPORT_PATH=FULL_BACKUP_REPORT_PATH,
		@LOG_BACKUP_REPORT_PATH=LOG_BACKUP_REPORT_PATH,
		@FULL_BACKUP_FILETAG=FULL_BACKUP_FILETAG,
		@LOG_BACKUP_FILETAG=LOG_BACKUP_FILETAG,
		@SHRINK_SIZE=ISNULL(SHRINK_SIZE,200)
	FROM DBO.APP_SETTING
	
	IF @DATA_SCHEMA_GRANT<>'ALL'
		return

	IF @BACKUP_FILETAG<>''
	BEGIN
		SET @FULL_BACKUP_FILETAG=@BACKUP_FILETAG
		SET @LOG_BACKUP_FILETAG=@BACKUP_FILETAG
	END

	IF EXISTS(SELECT * FROM DBO.BACKUP_TRACE where BACKUP_ID=@BACKUP_ID)
	BEGIN
		RAISERROR('backup_id is exists',11,1);
		return 1
	END

	DECLARE @VERSION_ID INT
	SET @VERSION_ID=convert(INT,DATABASEPROPERTYEX('master','version'))

	IF @TARGETDBNAME='%'
	BEGIN
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+'','')+'EXEC MSDB.DBO.SP_UPDATE_JOB @JOB_NAME= N'''+A.NAME+''',@ENABLED = 0;'
		FROM MSDB.DBO.SYSJOBS A
		WHERE A.NAME IN('TC_BACKUP_LOG')
		--PRINT(@SQL)
		EXEC(@SQL)
	END
	
	--如果有当前实例有其他备份进程,则等待3分钟
	WHILE EXISTS(SELECT 1 FROM SYS.DM_EXEC_REQUESTS WHERE COMMAND LIKE 'BACKUP%')
	BEGIN
		RAISERROR ('another backup process is running.wait 3 minute continue', 1,1)
		WAITFOR DELAY '00:03:00'
	END
	
	SET @SQL=''
	SELECT @SQL = ISNULL(@SQL+'','')+'ALTER DATABASE ['+NAME+'] SET RECOVERY FULL;'
	FROM SYS.DATABASES
	WHERE DATABASE_ID > 4 
		AND STATE = 0
		AND IS_READ_ONLY = 0
		AND RECOVERY_MODEL = 3
		AND IS_DISTRIBUTOR = 0
		AND NAME <> 'MONITOR'
		and name not like '%sysadmin%'
		and name NOT IN(SELECT NAME FROM MONITOR.DBO.MIRRORING_FILTER(NOLOCK))
	EXEC(@SQL)

	--定义变量
	DECLARE @CURRENT_TIME VARCHAR(20)
	DECLARE @START_TIME VARCHAR(25) = CONVERT(CHAR(19),GETDATE(),120)

	IF @TYPE = 1
		SELECT @BACKUP_PATH = (CASE WHEN @BACKUP_PATH<>'' THEN @BACKUP_PATH ELSE @FULL_BACKUP_PATH END),@KEEP_BACKUP_DAYS = @KEEP_FULL_BACKUP_DAYS,@DISK_MIN_SIZE_MB = @FULL_BACKUP_MIN_SIZE_MB,@SUFFIX = '.bak'
	ELSE IF @TYPE = 2
		SELECT @BACKUP_PATH = (CASE WHEN @BACKUP_PATH<>'' THEN @BACKUP_PATH ELSE @LOG_BACKUP_PATH END),@KEEP_BACKUP_DAYS = @KEEP_LOG_BACKUP_DAYS,@DISK_MIN_SIZE_MB = @LOG_BACKUP_MIN_SIZE_MB,@SUFFIX = '.trn'
	ELSE IF @TYPE = 3
		SELECT @SUFFIX = '.diff'
	
	select @BACKUP_PATH

	--删除旧文件
	SET @CMD ='FORFILES /P '+@BACKUP_PATH+' /M *'+@SUFFIX+' /S /D '+LTRIM(-1*@KEEP_BACKUP_DAYS)+' /C "CMD /C DEL @file"'
	EXEC XP_CMDSHELL @CMD
	
	EXEC @CHECKER = DBO.TOOL_CHECK_DISK_FREE_SIZE @BACKUP_PATH,@DISK_MIN_SIZE_MB
	IF @CHECKER = 0
	BEGIN
		--删除1天前的文件
		SET @CMD ='FORFILES /P '+@BACKUP_PATH+' /M *'+@SUFFIX+' /S /D -1 /C "CMD /C DEL @file"'
		EXEC XP_CMDSHELL @CMD
		
		EXEC @CHECKER = DBO.TOOL_CHECK_DISK_FREE_SIZE @BACKUP_PATH,@DISK_MIN_SIZE_MB
		IF @CHECKER = 0
		BEGIN
			SET @SQL = NULL
			SELECT @SQL = ISNULL(@SQL+'','')+'EXEC MSDB.DBO.SP_UPDATE_JOB @JOB_NAME= N'''+A.NAME+''',@ENABLED = 1;'
			FROM MSDB.DBO.SYSJOBS A
			WHERE A.NAME IN('TC_BACKUP_LOG')
			--PRINT(@SQL)
			EXEC(@SQL)
			
			SET @ERROR_MESSAGE = 'DISK_FREE_SIZE_MB LESS THAN '+LTRIM(@DISK_MIN_SIZE_MB)+' MB,BACKUP FAIL.'
			RAISERROR(@ERROR_MESSAGE,11,1);
		END
	END

	DECLARE @DBLIST VARCHAR(8000)
	

	IF @TARGETDBNAME='%'
		SELECT @DBLIST=STUFF((SELECT ',' + name FROM master.sys.databases where database_id>4 and name not in('Monitor') and name not in(select name from Monitor.dbo.BACKUP_FILTER) FOR XML PATH('')), 1, 2, '');
	ELSE
		SET @DBLIST=@TARGETDBNAME

	DECLARE @BACKUP_TASK_START_TIME VARCHAR(100)
	DECLARE @BACKUP_TASK_END_TIME VARCHAR(100)

	SET @BACKUP_TASK_START_TIME=convert(varchar(19),getdate(),121)

	BEGIN TRY
		--开始备份
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+CHAR(13),'')+'
		DECLARE @SUCCESS_'+NAME+' INT = 0,@CHECKER_'+NAME+' INT = 0
		DECLARE @STARTTIME_'+NAME+' VARCHAR(25) = CONVERT(CHAR(19),GETDATE(),120),
			@STARTTIME_SHORT_'+NAME+' VARCHAR(25) =REPLACE(REPLACE(REPLACE(CONVERT(CHAR(19),GETDATE(),120),'':'',''''),''-'',''''),'' '','''')
		DECLARE @FILENAME_'+NAME+' VARCHAR(4000) = '''+NAME+'__'+@APP+'_'+@IP+'_'+LTRIM(@PORT)+'_''+@STARTTIME_SHORT_'+NAME+'+'''+@SUFFIX+'''
		DECLARE @FULLFILENAME_'+NAME+' VARCHAR(4000) = '''+@BACKUP_PATH+'''+@FILENAME_'+NAME+'
		EXEC @CHECKER_'+NAME+' = DBO.TOOL_CHECK_DISK_FREE_SIZE '''+@BACKUP_PATH+''','+LTRIM(@DISK_MIN_SIZE_MB)+'
		IF @CHECKER_'+NAME+' = 1
		BEGIN
			IF '+LTRIM(@TYPE)+' <> 1 AND EXISTS(SELECT 1 FROM SYS.MASTER_FILES A,Monitor.DBO.BACKUP_DBLIST B WHERE A.DATABASE_ID = B.DATABASE_ID AND B.NAME = '''+NAME+''' AND A.TYPE = 0 AND A.DIFFERENTIAL_BASE_LSN IS NULL)
			BEGIN
				DECLARE @NEWFULLFILENAME_'+NAME+' VARCHAR(4000) = REPLACE(REPLACE(@FULLFILENAME_'+NAME+','''+@SUFFIX+''',''.bak''),'''+@BACKUP_PATH+''','''+@FULL_BACKUP_PATH+''')
				EXEC @SUCCESS_'+NAME+' = DBO.TOOL_BACKUP_DATABASE_OPERATOR 1,'''+NAME+''',@NEWFULLFILENAME_'+NAME+'
			END
			EXEC @SUCCESS_'+NAME+' = DBO.TOOL_BACKUP_DATABASE_OPERATOR '+LTRIM(@TYPE)+','''+NAME+''',@FULLFILENAME_'+NAME+'
		END
		DECLARE @ENDTIME_'+NAME+' VARCHAR(25) = CONVERT(CHAR(19),GETDATE(),120)
		INSERT INTO DBO.BACKUP_TRACE(BACKUP_ID,DBNAME,[PATH],FILENAME,TYPE,STARTTIME,ENDTIME,FILESIZE,MD5CODE,SUCCESS,UPLOADED,WRITETIME)
		VALUES('''+@BACKUP_ID+''','''+NAME+''','''+@BACKUP_PATH+''',@FILENAME_'+NAME+','+LTRIM(@TYPE)+',@STARTTIME_'+NAME+',@ENDTIME_'+NAME+',0,0,@SUCCESS_'+NAME+',0,GETDATE())'
		FROM DBO.BACKUP_DBLIST WHERE NAME in(select RowValue from dbo.SplitStringByRow(@DBLIST,','))
		--PRINT(@SQL)
		EXEC (@SQL)
	END TRY
	BEGIN CATCH
		PRINT '~~ error in backup database ~~'
	END CATCH

	SET @BACKUP_TASK_END_TIME=convert(varchar(19),getdate(),121)

	DECLARE @DBNAME VARCHAR(1000),@PATH VARCHAR(1000),@FILENAME VARCHAR(1000),@STARTTIME VARCHAR(100),@ENDTIME VARCHAR(100),@FILESIZE VARCHAR(100)
	DECLARE @BACKUP_STR VARCHAR(MAX),@TASK_ID VARCHAR(100)
	DECLARE @FILECNT BIGINT,@DBSIZE BIGINT,@DBLEVEL BIGINT

	IF OBJECT_ID('TEMPDB.DBO.#baklist','U') IS NOT NULL
		DROP TABLE #baklist

	CREATE TABLE #baklist(
	BackupName nvarchar(128),
	BackupDescription nvarchar(255),
	BackupType smallint,
	ExpirationDate datetime,
	Compressed tinyint,
	Position smallint,
	DeviceType tinyint,
	UserName nvarchar(128),
	ServerName nvarchar(128),
	DatabaseName nvarchar(128),
	DatabaseVersion int,
	DatabaseCreationDate datetime,
	BackupSize numeric(20,0),
	FirstLSN numeric(25,0),
	LastLSN numeric(25,0),
	CheckpointLSN numeric(25,0),
	DatabaseBackupLSN numeric(25,0),
	BackupStartDate datetime,
	BackupFinishDate datetime,
	SortOrder smallint,
	CodePage smallint,
	UnicodeLocaleId int,
	UnicodeComparisonStyle int,
	CompatibilityLevel tinyint,
	SoftwareVendorId int,
	SoftwareVersionMajor int,
	SoftwareVersionMinor int,
	SoftwareVersionBuild int,
	MachineName nvarchar(128),
	Flags int,
	BindingID uniqueidentifier,
	RecoveryForkID uniqueidentifier,
	Collation nvarchar(128),
	FamilyGUID uniqueidentifier,
	HasBulkLoggedData bit,
	IsSnapshot bit,
	IsReadOnly bit,
	IsSingleUser bit,
	HasBackupChecksums bit,
	IsDamaged bit,
	BeginsLogChain bit,
	HasIncompleteMetaData bit,
	IsForceOffline bit,
	IsCopyOnly bit,
	FirstRecoveryForkID uniqueidentifier,
	ForkPointLSN numeric(25,0) NULL,
	RecoveryModel nvarchar(60),
	DifferentialBaseLSN numeric(25,0) NULL,
	DifferentialBaseGUID uniqueidentifier,
	BackupTypeDescription nvarchar(60),
	BackupSetGUID uniqueidentifier NULL,
	CompressedBackupSize bigint,
	Containment bigint,
	KeyAlgorithm nvarchar(32),
	EncryptorThumbprint varbinary(20),
	EncryptorType nvarchar(32),
	LastValidRestoreTime datetime,
	TimeZone nvarchar(32),
	CompressionAlgorithm nvarchar(32)
	)

	IF OBJECT_ID('TEMPDB.DBO.#logical','U') IS NOT NULL
		DROP TABLE #logical

	CREATE TABLE #logical(
		LogicalName nvarchar(128),
		Physicalname nvarchar(260),
		Type char(1),
		FileGroupName nvarchar(128),
		Size numeric(20,0),
		MaxSize numeric(20),
		FileID bigint,
		CreateLSN numeric(25,0),
		DropLSN numeric(25,0) NULL,
		UniqueID uniqueidentifier,
		ReadOnlyLSN numeric(25,0) NULL,
		ReadWriteLSN numeric(25,0) NULL,
		BackupSizeInBytes bigint,
		SourceBlockSize int,
		FileGroupID int ,
		LogGroupGUID uniqueidentifier NULL,
		DifferentialBaseLSN numeric(25,0) NULL,
		DifferentialBaseGUID uniqueidentifier,
		IsReadOnly bit,
		IsPresent bit,
		TDEThumbprint varbinary(32),
		SnapshotUrl nvarchar(360)
	)

	SELECT @FILECNT=count(1) FROM MONITOR.DBO.BACKUP_TRACE WHERE BACKUP_ID=@BACKUP_ID

	DECLARE @BakFile VARCHAR(1000)
	DECLARE dblist_cur cursor static forward_only Read_only for 
	SELECT DBNAME,PATH,FILENAME,convert(varchar(19),STARTTIME,121),convert(varchar(19),ENDTIME,121) FROM MONITOR.DBO.BACKUP_TRACE WHERE BACKUP_ID=@BACKUP_ID
	OPEN dblist_cur;
	FETCH NEXT FROM dblist_cur INTO @DBNAME,@PATH,@FILENAME,@STARTTIME,@ENDTIME
	WHILE @@FETCH_STATUS = 0
	BEGIN
		SET @BakFile=@PATH+@FILENAME

		DELETE FROM #logical
		SELECT @SQL = 'RESTORE FILELISTONLY FROM DISK=@BakFile WITH FILE = 1'

		IF @VERSION_ID>=852
		BEGIN
			INSERT #logical(LogicalName,Physicalname,Type,FileGroupName,Size,MaxSize,FileID,CreateLSN,DropLSN,UniqueID,ReadOnlyLSN,ReadWriteLSN,BackupSizeInBytes,SourceBlockSize,FileGroupID,LogGroupGUID,DifferentialBaseLSN,DifferentialBaseGUID,IsReadOnly,IsPresent,TDEThumbprint,SnapshotUrl)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END
		ELSE
		BEGIN
			INSERT #logical(LogicalName,Physicalname,Type,FileGroupName,Size,MaxSize,FileID,CreateLSN,DropLSN,UniqueID,ReadOnlyLSN,ReadWriteLSN,BackupSizeInBytes,SourceBlockSize,FileGroupID,LogGroupGUID,DifferentialBaseLSN,DifferentialBaseGUID,IsReadOnly,IsPresent,TDEThumbprint)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END

		DELETE FROM #baklist
		SELECT @SQL = 'RESTORE HEADERONLY FROM DISK=@BakFile'
		IF(@VERSION_ID=661 or @VERSION_ID=665)
		BEGIN
			INSERT #baklist(BackupName,BackupDescription,BackupType,ExpirationDate,Compressed,Position,DeviceType,UserName,ServerName,DatabaseName,DatabaseVersion,DatabaseCreationDate,BackupSize,FirstLSN,LastLSN,CheckpointLSN,DatabaseBackupLSN,BackupStartDate,BackupFinishDate,SortOrder,CodePage,UnicodeLocaleId,UnicodeComparisonStyle,CompatibilityLevel,SoftwareVendorId,SoftwareVersionMajor,SoftwareVersionMinor,SoftwareVersionBuild,MachineName,Flags,BindingID,RecoveryForkID,Collation,FamilyGUID,HasBulkLoggedData,IsSnapshot,IsReadOnly,IsSingleUser,HasBackupChecksums,IsDamaged,BeginsLogChain,HasIncompleteMetaData,IsForceOffline,IsCopyOnly,FirstRecoveryForkID,ForkPointLSN,RecoveryModel,DifferentialBaseLSN,DifferentialBaseGUID,BackupTypeDescription,BackupSetGUID,CompressedBackupSize)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END
		ELSE IF(@VERSION_ID=611 or @VERSION_ID=612)
		BEGIN
			INSERT #baklist(BackupName,BackupDescription,BackupType,ExpirationDate,Compressed,Position,DeviceType,UserName,ServerName,DatabaseName,DatabaseVersion,DatabaseCreationDate,BackupSize,FirstLSN,LastLSN,CheckpointLSN,DatabaseBackupLSN,BackupStartDate,BackupFinishDate,SortOrder,CodePage,UnicodeLocaleId,UnicodeComparisonStyle,CompatibilityLevel,SoftwareVendorId,SoftwareVersionMajor,SoftwareVersionMinor,SoftwareVersionBuild,MachineName,Flags,BindingID,RecoveryForkID,Collation,FamilyGUID,HasBulkLoggedData,IsSnapshot,IsReadOnly,IsSingleUser,HasBackupChecksums,IsDamaged,BeginsLogChain,HasIncompleteMetaData,IsForceOffline,IsCopyOnly,FirstRecoveryForkID,ForkPointLSN,RecoveryModel,DifferentialBaseLSN,DifferentialBaseGUID,BackupTypeDescription,BackupSetGUID,CompressedBackupSize)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END
		ELSE IF(@VERSION_ID=706)
		BEGIN
			INSERT #baklist(BackupName,BackupDescription,BackupType,ExpirationDate,Compressed,Position,DeviceType,UserName,ServerName,DatabaseName,DatabaseVersion,DatabaseCreationDate,BackupSize,FirstLSN,LastLSN,CheckpointLSN,DatabaseBackupLSN,BackupStartDate,BackupFinishDate,SortOrder,CodePage,UnicodeLocaleId,UnicodeComparisonStyle,CompatibilityLevel,SoftwareVendorId,SoftwareVersionMajor,SoftwareVersionMinor,SoftwareVersionBuild,MachineName,Flags,BindingID,RecoveryForkID,Collation,FamilyGUID,HasBulkLoggedData,IsSnapshot,IsReadOnly,IsSingleUser,HasBackupChecksums,IsDamaged,BeginsLogChain,HasIncompleteMetaData,IsForceOffline,IsCopyOnly,FirstRecoveryForkID,ForkPointLSN,RecoveryModel,DifferentialBaseLSN,DifferentialBaseGUID,BackupTypeDescription,BackupSetGUID,CompressedBackupSize,Containment)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END
		ELSE IF(@VERSION_ID>=957)
		BEGIN
			INSERT #baklist(BackupName,BackupDescription,BackupType,ExpirationDate,Compressed,Position,DeviceType,UserName,ServerName,DatabaseName,DatabaseVersion,DatabaseCreationDate,BackupSize,FirstLSN,LastLSN,CheckpointLSN,DatabaseBackupLSN,BackupStartDate,BackupFinishDate,SortOrder,CodePage,UnicodeLocaleId,UnicodeComparisonStyle,CompatibilityLevel,SoftwareVendorId,SoftwareVersionMajor,SoftwareVersionMinor,SoftwareVersionBuild,MachineName,Flags,BindingID,RecoveryForkID,Collation,FamilyGUID,HasBulkLoggedData,IsSnapshot,IsReadOnly,IsSingleUser,HasBackupChecksums,IsDamaged,BeginsLogChain,HasIncompleteMetaData,IsForceOffline,IsCopyOnly,FirstRecoveryForkID,ForkPointLSN,RecoveryModel,DifferentialBaseLSN,DifferentialBaseGUID,BackupTypeDescription,BackupSetGUID,CompressedBackupSize,Containment,KeyAlgorithm,EncryptorThumbprint,EncryptorType,LastValidRestoreTime,TimeZone,CompressionAlgorithm)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END
		ELSE
		BEGIN
			INSERT #baklist(BackupName,BackupDescription,BackupType,ExpirationDate,Compressed,Position,DeviceType,UserName,ServerName,DatabaseName,DatabaseVersion,DatabaseCreationDate,BackupSize,FirstLSN,LastLSN,CheckpointLSN,DatabaseBackupLSN,BackupStartDate,BackupFinishDate,SortOrder,CodePage,UnicodeLocaleId,UnicodeComparisonStyle,CompatibilityLevel,SoftwareVendorId,SoftwareVersionMajor,SoftwareVersionMinor,SoftwareVersionBuild,MachineName,Flags,BindingID,RecoveryForkID,Collation,FamilyGUID,HasBulkLoggedData,IsSnapshot,IsReadOnly,IsSingleUser,HasBackupChecksums,IsDamaged,BeginsLogChain,HasIncompleteMetaData,IsForceOffline,IsCopyOnly,FirstRecoveryForkID,ForkPointLSN,RecoveryModel,DifferentialBaseLSN,DifferentialBaseGUID,BackupTypeDescription,BackupSetGUID,CompressedBackupSize,Containment,KeyAlgorithm,EncryptorThumbprint,EncryptorType)
			EXEC sp_executesql @SQL,N'@BakFile nvarchar(512)', @BakFile=@BakFile
		END

		SELECT @DBSIZE=sum(Size)/1024 FROM #logical
		SELECT @FILESIZE=CompressedBackupSize/1024,@DBLEVEL=CompatibilityLevel FROM #baklist

		IF @TYPE=1
			SET @CMD=@BACKUP_CLIENT_PATH+' register -f "'+@BakFile+'" -t '+@FULL_BACKUP_FILETAG+' --storage-type='+@BACKUP_STORAGE_TYPE
		ELSE
			SET @CMD=@BACKUP_CLIENT_PATH+' register -f "'+@BakFile+'" -t '+@LOG_BACKUP_FILETAG+' --storage-type='+@BACKUP_STORAGE_TYPE

		BEGIN TRY
			TRUNCATE TABLE DBO.BACKUP_COMMON_TABLE
			INSERT INTO DBO.BACKUP_COMMON_TABLE EXEC XP_CMDSHELL @CMD
		END TRY
		BEGIN CATCH
			PRINT '~~ error in backup database ~~'
		END CATCH

		DELETE FROM DBO.BACKUP_COMMON_TABLE WHERE NOT ISNUMERIC(BLOCK) = 1

		IF EXISTS(SELECT 1 FROM DBO.BACKUP_COMMON_TABLE)
			SELECT @TASK_ID = BLOCK FROM DBO.BACKUP_COMMON_TABLE
		ELSE
			SET @TASK_ID='0'
		
		IF @TYPE=1
		BEGIN
			SET @BACKUP_STR='{"cluster_id":'+@CLUSTER_ID+',"cluster_address":"'+@CLUSTER_DOMAIN+'","backup_host":"'+@IP+'","backup_port":'+@PORT+',"master_ip":"'+@MASTER_IP+'","master_port":'+@MASTER_PORT+',"role":"'+@ROLE+'","backup_type":"'+@BACKUP_TYPE+'","bill_id":"","bk_biz_id":'+@BK_BIZ_ID+',"bk_cloud_id":'+@BK_CLOUD_ID+',"charset":"'+@CHARSET+'","time_zone":"'+@TIME_ZONE+'","version":"'+@VERSION+'","data_schema_grant":"'+@DATA_SCHEMA_GRANT+'","is_full_backup":'+(case when @TYPE=1  then 'true' else 'false' end) +',"backup_id":"'+@BACKUP_ID+'","backup_task_start_time":"'+replace(@BACKUP_TASK_START_TIME,' ' ,'T')+@TIME_ZONE+'","backup_task_end_time":"'+replace(@BACKUP_TASK_END_TIME,' ' ,'T')+@TIME_ZONE+'","db_list":"'+@DBLIST+'","file_cnt":'+convert(varchar,@FILECNT)+',"task_id":"'+@TASK_ID+'","dbname":"'+@DBNAME+'","backup_begin_time":"'+replace(@STARTTIME,' ' ,'T')+@TIME_ZONE+'","backup_end_time":"'+replace(@ENDTIME,' ' ,'T')+@TIME_ZONE+'","file_name":"'+@FILENAME+'","file_size_kb":'+convert(varchar,@FILESIZE)+',"db_size_kb":'+convert(varchar,@DBSIZE)+',"compatibility_level":'+convert(varchar,@DBLEVEL)+',"local_path":"'+replace(@FULL_BACKUP_PATH,'\','\\')+'"}'
			SET @CMD = 'echo '+@BACKUP_STR+'>>D:\dbbak\backup_result.log' 
		END
		ELSE
		BEGIN
			SET @BACKUP_STR='{"cluster_id":'+@CLUSTER_ID+',"cluster_domain":"'+@CLUSTER_DOMAIN+'","db_role":"'+@ROLE+'","host":"'+@IP+'","port":'+@PORT+',"bk_biz_id":'+@BK_BIZ_ID+',"bk_cloud_id":'+@BK_CLOUD_ID+',"backup_id":"'+@BACKUP_ID+'","file_name":"'+@FILENAME+'","size":'+convert(varchar,@FILESIZE)+',"backup_task_start_time":"'+replace(@BACKUP_TASK_START_TIME,' ' ,'T')+@TIME_ZONE+'","backup_task_end_time":"'+replace(@BACKUP_TASK_END_TIME,' ' ,'T')+@TIME_ZONE+'","backup_begin_time":"'+replace(@STARTTIME,' ' ,'T')+@TIME_ZONE+'","backup_end_time":"'+replace(@ENDTIME,' ' ,'T')+@TIME_ZONE+'","backup_status":4,"backup_status_info":"","task_id":"'+@TASK_ID+'","dbname":"'+@DBNAME+'","file_cnt":'+convert(varchar,@FILECNT)+',"local_path":"'+replace(@LOG_BACKUP_PATH,'\','\\')+'"}'
			SET @CMD = 'echo '+@BACKUP_STR+'>>D:\dbbak\binlog_result.log' 
		END
		PRINT @CMD
		EXEC XP_CMDSHELL @CMD

		FETCH NEXT FROM dblist_cur INTO @DBNAME,@PATH,@FILENAME,@STARTTIME,@ENDTIME;
	END
	CLOSE dblist_cur;
	DEALLOCATE dblist_cur;

	IF @TARGETDBNAME='%'
	BEGIN
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+'','')+'EXEC MSDB.DBO.SP_UPDATE_JOB @JOB_NAME= N'''+A.NAME+''',@ENABLED = 1;'
		FROM MSDB.DBO.SYSJOBS A
		WHERE A.NAME IN('TC_BACKUP_LOG')
		--PRINT(@SQL)
		EXEC(@SQL)
	END
	
	IF @DATA_SCHEMA_GRANT='all'
	BEGIN
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+';'+CHAR(13),'')+'USE ['+A.NAME+'] DBCC SHRINKFILE ('''+B.NAME+''','+convert(varchar,@shrink_size)+')'
		FROM SYS.DATABASES A,SYS.MASTER_FILES B
		WHERE A.DATABASE_ID > 4
			AND A.NAME <> 'MONITOR'
			AND A.STATE = 0
			AND A.IS_READ_ONLY = 0
			AND A.DATABASE_ID = B.DATABASE_ID
			AND B.TYPE = 1
			AND B.SIZE*8/1024/1024 >= @SHRINK_SIZE
		--PRINT(@SQL)
		EXEC(@SQL)
	END


END


GO

/****** Object:  StoredProcedure [dbo].[TOOL_BACKUP_DATABASE_OPERATOR]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



CREATE PROCEDURE [dbo].[TOOL_BACKUP_DATABASE_OPERATOR]
@TYPE INT,
@DBNAME VARCHAR(100),
@FILENAME VARCHAR(1000)
AS
BEGIN
	SET NOCOUNT ON
	DECLARE @SQL VARCHAR(8000) = '
	BACKUP '+CASE WHEN @TYPE = 2 THEN 'LOG' ELSE 'DATABASE' END+' ['+@DBNAME+']
	TO DISK = '''+@FILENAME+'''
	WITH INIT,STATS = 10 '+CASE WHEN @TYPE = 3 THEN ',DIFFERENTIAL' ELSE '' END+'
	'
	--PRINT(@SQL)
	EXEC(@SQL)
    IF @@ERROR <> 0 
		RETURN 0
	ELSE RETURN 1
END



GO

/****** Object:  StoredProcedure [dbo].[TOOL_CHECK_DISK_FREE_SIZE]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO



CREATE PROCEDURE [dbo].[TOOL_CHECK_DISK_FREE_SIZE]
@BACKUP_PATH VARCHAR(1000),
@FREE_SIZE_MB INT
AS
BEGIN
	SET NOCOUNT ON
	DECLARE @DISKCUR INT = 0
	IF OBJECT_ID('TEMPDB.DBO.#DISKFREE','U') IS NOT NULL
		DROP TABLE #DISKFREE
	CREATE TABLE #DISKFREE(LABEL VARCHAR(100) NOT NULL,FREEMB INT NOT NULL)
	INSERT INTO #DISKFREE EXEC MASTER.DBO.XP_FIXEDDRIVES
	SELECT @DISKCUR = ISNULL(FREEMB,0) FROM #DISKFREE WHERE LABEL = LEFT(@BACKUP_PATH,1)
	IF @DISKCUR < @FREE_SIZE_MB
		RETURN 0
	RETURN 1
END


GO

/****** Object:  StoredProcedure [dbo].[TOOL_GET_IPPORT]    Script Date: 2024/4/7 16:18:15 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO




CREATE PROC [dbo].[TOOL_GET_IPPORT]
@IP	VARCHAR(50) OUTPUT,
@PORT VARCHAR(10) OUTPUT
AS
BEGIN
	SELECT @IP=IP,@PORT=PORT FROM APP_SETTING

END



GO

/****** Object:  StoredProcedure [dbo].[TOOL_CHANGE_DBOWNER]    Script Date: 4/11/2024 3:24:11 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [dbo].[TOOL_CHANGE_DBOWNER]
AS

BEGIN

DECLARE @SQL VARCHAR(8000)

SELECT @SQL = ISNULL(@SQL+'','')+'EXEC ['+name+'].dbo.sp_changedbowner @loginame = N''sa'', @map = false;'
from master.sys.databases where database_id>4 and name not in('Monitor') and owner_sid<>0x01
--PRINT(@SQL)
EXEC(@SQL)

SELECT @SQL = ISNULL(@SQL+'','')+'EXEC msdb.dbo.sp_update_job @job_name=N'''+name+''', @owner_login_name=N''sa'';'
from msdb.dbo.sysjobs where owner_sid<>0x01
--PRINT(@SQL)
EXEC(@SQL)

END

GO




--***************************************** INIT DATA ***********************************

USE MONITOR
GO

USE MONITOR
GO
DECLARE @SERVERNAME VARCHAR(100)
SELECT top 1 @SERVERNAME=substring(object_name,0,charindex(':',object_name)) FROM MASTER.SYS.DM_OS_PERFORMANCE_COUNTERS(NOLOCK) where counter_name='Batch Requests/sec'

TRUNCATE TABLE DBO.MONITOR_INSANCE_COUNTER
INSERT INTO DBO.MONITOR_INSANCE_COUNTER(COUNTER_SHORT_NAME,OBJECT_NAME,COUNTER_NAME,INSTANCE_NAME)
SELECT 'mssql_transactions',			''+@SERVERNAME++':Databases',				'Transactions/sec',			'_Total' UNION ALL
SELECT 'mssql_connections',			''+@SERVERNAME++':General Statistics',	'User Connections',			'' UNION ALL
SELECT 'mssql_requests',				''+@SERVERNAME++':SQL Statistics',		'Batch Requests/sec',		'' UNION ALL
SELECT 'mssql_logins',				''+@SERVERNAME++':General Statistics',	'Logins/sec',				'' UNION ALL
SELECT 'mssql_logouts',				''+@SERVERNAME++':General Statistics',	'Logouts/sec',				'' UNION ALL
SELECT 'mssql_lock_requests',			''+@SERVERNAME++':Locks',					'Lock Requests/sec',		'Database' UNION ALL
SELECT 'mssql_user_errors',			''+@SERVERNAME++':SQL Errors',			'Errors/sec',				'User Errors' UNION ALL
SELECT 'mssql_sql_compilations',		''+@SERVERNAME++':SQL Statistics',		'SQL Compilations/sec',		'' UNION ALL
SELECT 'mssql_sql_recompilations',	''+@SERVERNAME++':SQL Statistics',		'SQL Re-Compilations/sec',	'' UNION ALL
SELECT 'mssql_full_scans',			''+@SERVERNAME++':Access Methods',		'Full Scans/sec',			'' UNION ALL
SELECT 'mssql_buffer_cache_hit_ratio',''+@SERVERNAME++':Buffer Manager',		'Buffer cache hit ratio',	'' UNION ALL
SELECT 'mssql_buffer_cache_hit_ratio_base',''+@SERVERNAME++':Buffer Manager',		'Buffer cache hit ratio base','' UNION ALL
SELECT 'mssql_latch_waits',			''+@SERVERNAME++':Latches',				'Latch Waits/sec',			'' UNION ALL
SELECT 'mssql_lock_waits',			''+@SERVERNAME++':Wait Statistics',		'Lock waits',				'Average Wait Time (ms)' UNION ALL
SELECT 'mssql_network_io_waits',		''+@SERVERNAME++':Wait Statistics',		'Network IO waits',			'Average Wait Time (ms)' UNION ALL
SELECT 'mssql_plan_cache_hit_ratio',	''+@SERVERNAME++':Plan Cache',			'Cache Hit Ratio',			'_Total' UNION ALL
SELECT 'mssql_plan_cache_hit_ratio_base',	''+@SERVERNAME++':Plan Cache',			'Cache Hit Ratio base',		'_Total' UNION ALL
SELECT 'mssql_total_memory',			''+@SERVERNAME++':Memory Manager',		'Total Server Memory (KB)','' UNION ALL
SELECT 'mssql_blocked_processes',		''+@SERVERNAME++':General Statistics',	'Processes blocked',		'' UNION ALL
SELECT 'mssql_target_memory',			''+@SERVERNAME++':Memory Manager',		'Target Server Memory (KB)','' UNION ALL
SELECT 'mssql_number_of_deadlocks',		''+@SERVERNAME++':Locks',	'Number of Deadlocks/sec',		'_Total'  UNION ALL
SELECT 'mssql_lazy_writes',		''+@SERVERNAME++':Buffer Manager',	'Lazy writes/sec',		''  UNION ALL
SELECT 'mssql_page_reads',		''+@SERVERNAME++':Buffer Manager',	'Page reads/sec',		''  UNION ALL
SELECT 'mssql_page_writes',		''+@SERVERNAME++':Buffer Manager',	'Page writes/sec',		''  UNION ALL
SELECT 'mssql_checkpoint_pages',		''+@SERVERNAME++':Buffer Manager',	'Checkpoint pages/sec',		''  UNION ALL
SELECT 'mssql_page_life_expectancy',		''+@SERVERNAME++':Buffer Manager',	'Page life expectancy',		'' 
GO
UPDATE DBO.MONITOR_INSANCE_COUNTER SET COMPUTE_INTERVAL = 1 WHERE COUNTER_NAME LIKE '%/sec'
GO

--****************************************** JOB ****************************************
USE [msdb]
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_BACKUP_FULL')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_BACKUP_FULL', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_BACKUP_LOG')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_BACKUP_LOG', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_MONITOR_FILTER')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_MONITOR_FILTER', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_SNAPSHOT')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_SNAPSHOT', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_SNAPSHOT_ONE')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_SNAPSHOT_ONE', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_TRACE')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_TRACE', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name = N'TC_UPDATESTATS')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_UPDATESTATS', @delete_unused_schedule=1
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs WHERE name=N'TC_AUTO_GRANT')
	EXEC msdb.dbo.sp_delete_job @job_name=N'TC_AUTO_GRANT', @delete_unused_schedule=1
GO

USE [msdb]
GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_BACKUP_FULL', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_BACKUP_FULL_1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_BACKUP_FULL_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC MONITOR.DBO.TOOL_BACKUP_DATABASE 1', 
		@database_name=N'master', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_BACKUP_FULL_1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=1, 
		@freq_subday_interval=26, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20071220, 
		@active_end_date=99991231, 
		@active_start_time=32600, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_BACKUP_LOG', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_BACKUP_LOG_1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_BACKUP_LOG_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC MONITOR.DBO.TOOL_BACKUP_DATABASE 2', 
		@database_name=N'master', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_BACKUP_LOG_1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=4, 
		@freq_subday_interval=30, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20101013, 
		@active_end_date=99991231, 
		@active_start_time=0, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_MONITOR_FILTER', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_MONITOR_FILTER_1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_MONITOR_FILTER_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC DBO.JOB_MONITOR_FILTER', 
		@database_name=N'MONITOR', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_MONITOR_FILTER_1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=4, 
		@freq_subday_interval=1, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20130821, 
		@active_end_date=99991231, 
		@active_start_time=0, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_SNAPSHOT', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'auto do snapshot in 00:10', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'exec monitor.dbo.JOB_SNAPSHOT', 
		@database_name=N'master', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=1, 
		@freq_subday_interval=30, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20120301, 
		@active_end_date=99991231, 
		@active_start_time=100, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_SNAPSHOT_ONE', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_SNAPSHOT_ONE_1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_SNAPSHOT_ONE_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC MONITOR.DBO.JOB_SNAPSHOT 1', 
		@database_name=N'master', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_SNAPSHOT_ONE_1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=1, 
		@freq_subday_interval=0, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20130723, 
		@active_end_date=99991231, 
		@active_start_time=10000, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_TRACE', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [step_1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'step_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC MONITOR.DBO.JOB_TRACE 1', 
		@database_name=N'MASTER', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'schedule_1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=4, 
		@freq_subday_interval=5, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20130723, 
		@active_end_date=99991231, 
		@active_start_time=0, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2024/4/7 14:30:10 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_UPDATESTATS', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_UPDATESTATS_1]    Script Date: 2024/4/7 14:30:10 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_UPDATESTATS_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC MONITOR.DBO.JOB_UPDATESTATS
', 
		@database_name=N'master', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_UPDATESTATS_1', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=1, 
		@freq_subday_interval=0, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20211018, 
		@active_end_date=99991231, 
		@active_start_time=10000, 
		@active_end_time=235959, 
		@schedule_uid=N'edcaf102-cf8f-4a5c-a2f4-32bb7e82b284'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_UPDATESTATS_7', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=1, 
		@freq_subday_interval=0, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20211018, 
		@active_end_date=99991231, 
		@active_start_time=70000, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO


BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0

IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_AUTO_GRANT', 
		@enabled=1, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_AUTO_GRANT', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC Monitor.DBO.JOB_AUTO_GRANT
', 
		@database_name=N'master', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_AUTO_GRANT', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=4, 
		@freq_subday_interval=1, 
		@freq_relative_interval=0, 
		@freq_recurrence_factor=0, 
		@active_start_date=20211018, 
		@active_end_date=99991231, 
		@active_start_time=0, 
		@active_end_time=235959
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N'(local)'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
COMMIT TRANSACTION
GOTO EndSave
QuitWithRollback:
    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION
EndSave:

GO

