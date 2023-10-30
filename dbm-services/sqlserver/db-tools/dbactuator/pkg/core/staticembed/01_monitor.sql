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
DECLARE @SQL VARCHAR(MAX) = '
CREATE DATABASE Monitor
ON PRIMARY
(NAME = ''Monitor'',FILENAME = ''D:\gamedb\Monitor_'+@@SERVICENAME+'.mdf'',SIZE = 100MB,MAXSIZE = UNLIMITED,FILEGROWTH = 100MB)
LOG ON
(NAME = ''Monitor_log'',FILENAME = ''D:\gamedb\Monitor_'+@@SERVICENAME+'.ldf'',SIZE = 100MB,MAXSIZE = 2048GB,FILEGROWTH = 100MB)
COLLATE Chinese_PRC_CI_AS'
--PRINT(@SQL)
EXEC(@SQL)
GO
ALTER DATABASE [Monitor] SET COMPATIBILITY_LEVEL = 100
GO
ALTER DATABASE [Monitor] SET ANSI_NULL_DEFAULT OFF
ALTER DATABASE [Monitor] SET ANSI_NULLS OFF
ALTER DATABASE [Monitor] SET ANSI_PADDING OFF
ALTER DATABASE [Monitor] SET ANSI_WARNINGS OFF
ALTER DATABASE [Monitor] SET ARITHABORT OFF
ALTER DATABASE [Monitor] SET AUTO_CLOSE OFF
ALTER DATABASE [Monitor] SET AUTO_CREATE_STATISTICS ON
ALTER DATABASE [Monitor] SET AUTO_SHRINK OFF
ALTER DATABASE [Monitor] SET AUTO_UPDATE_STATISTICS ON
ALTER DATABASE [Monitor] SET CURSOR_CLOSE_ON_COMMIT OFF
ALTER DATABASE [Monitor] SET CURSOR_DEFAULT GLOBAL 
ALTER DATABASE [Monitor] SET CONCAT_NULL_YIELDS_NULL OFF
ALTER DATABASE [Monitor] SET NUMERIC_ROUNDABORT OFF
ALTER DATABASE [Monitor] SET QUOTED_IDENTIFIER ON
ALTER DATABASE [Monitor] SET RECURSIVE_TRIGGERS OFF
ALTER DATABASE [Monitor] SET DISABLE_BROKER
ALTER DATABASE [Monitor] SET AUTO_UPDATE_STATISTICS_ASYNC ON
ALTER DATABASE [Monitor] SET DATE_CORRELATION_OPTIMIZATION OFF
ALTER DATABASE [Monitor] SET TRUSTWORTHY OFF
ALTER DATABASE [Monitor] SET ALLOW_SNAPSHOT_ISOLATION OFF
ALTER DATABASE [Monitor] SET PARAMETERIZATION SIMPLE
ALTER DATABASE [Monitor] SET READ_COMMITTED_SNAPSHOT OFF
ALTER DATABASE [Monitor] SET HONOR_BROKER_PRIORITY OFF
ALTER DATABASE [Monitor] SET READ_WRITE
ALTER DATABASE [Monitor] SET RECOVERY SIMPLE
ALTER DATABASE [Monitor] SET MULTI_USER
ALTER DATABASE [Monitor] SET PAGE_VERIFY CHECKSUM
ALTER DATABASE [Monitor] SET DB_CHAINING OFF
GO

--****************************************** LOGIN ****************************************
IF SUSER_SID('monitor') IS NOT NULL
	DROP LOGIN monitor
CREATE LOGIN monitor WITH PASSWORD=N'2zhlmcNdffff',DEFAULT_DATABASE=[MASTER],SID=0xADDEFF187E19CB4593D2DB00A0D287B1,CHECK_POLICY=OFF;
GO


--****************************************** PRINCIPAL ****************************************
USE Monitor
GO
IF DATABASE_PRINCIPAL_ID('monitor') IS NOT NULL
	DROP USER monitor
GO
CREATE USER monitor FOR LOGIN monitor WITH DEFAULT_SCHEMA=[dbo]
GO
EXEC SP_ADDROLEMEMBER N'db_owner',N'monitor'
GO

--****************************************** TABLE ****************************************

--监控_实例名(默认实例的监控名比较特殊,为SQLSERVER,非默认为MSSQL$INSTANCENAME)
IF OBJECT_ID('DBO.MONITOR_SERVICE','U') IS NULL
CREATE TABLE DBO.MONITOR_SERVICE
(
	NAME VARCHAR(100) NULL,
	MONITOR_SERVICE_NAME VARCHAR(100) NULL,
	PORT INT NULL
)
GO

--监控_监控项的明细路径
IF OBJECT_ID('DBO.MONITOR_COUNTERPATH','U') IS NULL
CREATE TABLE DBO.MONITOR_COUNTERPATH
(
	TYPE INT NULL,					--0.OS/1.DB
	COUNTERPATH VARCHAR(1000) NULL
)
GO

--不需要备份的数据库
IF OBJECT_ID('DBO.BACKUP_FILTER','U') IS NULL
CREATE TABLE DBO.BACKUP_FILTER
(
	NAME VARCHAR(100) NOT NULL
)
GO

IF OBJECT_ID('DBO.MONITOR_SERVER_SETTING','U') IS NULL
CREATE TABLE DBO.MONITOR_SERVER_SETTING
(
	INDEXNO INT NOT NULL,
	IP VARCHAR(100) NOT NULL,
	PORT VARCHAR(100) NOT NULL,
	DBNAME VARCHAR(100) NOT NULL,
	ACCOUNT VARCHAR(100) NOT NULL,
	PWD VARCHAR(100) NOT NULL,
	[STATE] INT NOT NULL
)
GO
IF OBJECT_ID('DBO.MONITOR_SERVER_UNAVAILABLE_HISTORY','U') IS NULL
CREATE TABLE DBO.MONITOR_SERVER_UNAVAILABLE_HISTORY
(
	IP VARCHAR(100) NOT NULL,
	PORT VARCHAR(100) NOT NULL,
	DBNAME VARCHAR(100) NOT NULL,
	ACCOUNT VARCHAR(100) NOT NULL,
	PWD VARCHAR(100) NOT NULL,
	WRITETIME DATETIME NOT NULL
)
GO

IF OBJECT_ID('DBO.BACKUP_SETTING','U') IS NULL
CREATE TABLE DBO.BACKUP_SETTING
(
	APP VARCHAR(100) NOT NULL,
	FULL_BACKUP_PATH VARCHAR(100) NOT NULL,
	LOG_BACKUP_PATH VARCHAR(100) NOT NULL,
	KEEP_FULL_BACKUP_DAYS INT NOT NULL,
	KEEP_LOG_BACKUP_DAYS INT NOT NULL,
	FULL_BACKUP_MIN_SIZE_MB INT NOT NULL,
	LOG_BACKUP_MIN_SIZE_MB INT NOT NULL,
	UPLOAD INT NOT NULL,
	MD5 INT NOT NULL,
	CONSTRAINT CK_FULLBACKUPMINSIZEMB CHECK(FULL_BACKUP_MIN_SIZE_MB > 10240),
	CONSTRAINT CK_LOGBACKUPMINSIZEMB CHECK(LOG_BACKUP_MIN_SIZE_MB > 10240)
)
GO


IF OBJECT_ID('DBO.BACKUP_TRACE','U') IS NULL
CREATE TABLE DBO.BACKUP_TRACE
(
	DBNAME VARCHAR(100) NOT NULL,
	PATH  VARCHAR(1000) NOT NULL,
	FILENAME VARCHAR(1000) NOT NULL,
	TYPE INT NOT NULL,
	STARTTIME DATETIME NOT NULL,
	ENDTIME DATETIME NOT NULL,
	DURATION AS DATEDIFF(SECOND,STARTTIME,ENDTIME),
	FILESIZE [BIGINT] NULL,
	MD5CODE VARCHAR(100) NOT NULL,
	SUCCESS INT NOT NULL,
	UPLOADED INT NOT NULL,
	WRITETIME DATETIME NOT NULL,
	CONSTRAINT PK_BACKUP_TRACE_FILENAME PRIMARY KEY NONCLUSTERED(FILENAME)
)
GO
IF NOT EXISTS(SELECT 1 FROM SYS.INDEXES WHERE NAME = 'IDX_CL_BACKUP_TRACE_STARTTIME')
	CREATE CLUSTERED INDEX IDX_CL_BACKUP_TRACE_STARTTIME ON DBO.BACKUP_TRACE(STARTTIME)
GO


--公用表,用于记录文件大小和MD5值
IF OBJECT_ID('DBO.BACKUP_COMMON_TABLE','U') IS NULL
CREATE TABLE DBO.BACKUP_COMMON_TABLE
(
	BLOCK VARCHAR(8000)
)
GO

--跟踪设置
IF OBJECT_ID('DBO.TRACE_SETTING','U') IS NULL
CREATE TABLE DBO.TRACE_SETTING
(
	NAME VARCHAR(100) NOT NULL,	
	VALUE INT NOT NULL				
)
GO

--存放当前运行的跟踪信息
IF OBJECT_ID('DBO.TRACE_CURRENT_TRACEINFO','U') IS NULL
CREATE TABLE DBO.TRACE_CURRENT_TRACEINFO
(
	STARTTIME DATETIME NOT NULL,
	TRACEID INT NOT NULL,
	TRACEFILE VARCHAR(100) NOT NULL
)
GO

--存放跟踪出的SQL
IF OBJECT_ID('DBO.TRACE_TSQL','U') IS NULL
CREATE TABLE DBO.TRACE_TSQL
(
	SQLTXT VARCHAR(8000) NULL,
	SQLCHECKSUM BIGINT NULL,
	TEXTDATA VARCHAR(8000) NULL,
	APPLICATIONNAME VARCHAR(5000) NULL,
	NTUSERNAME VARCHAR(5000) NULL,
	LOGINNAME VARCHAR(5000) NULL,
	DURATION BIGINT NOT NULL,
	STARTTIME DATETIME NULL,
	ENDTIME DATETIME NULL,
	READS BIGINT NULL,
	WRITES BIGINT NULL,
	CPU INT NULL,
	SERVERNAME VARCHAR(500) NULL,
	ERROR BIGINT NULL,
	OBJECTID BIGINT NULL,
	OBJECTNAME VARCHAR(5000) NULL,
	DATABASENAME VARCHAR(1000) NULL,
	ROWCOUNTS BIGINT NULL
)
IF NOT EXISTS(SELECT 1 FROM SYS.INDEXES WHERE NAME = 'IDX_CL_TRACETSQL_STARTTIME')
	CREATE CLUSTERED INDEX IDX_CL_TRACETSQL_STARTTIME ON DBO.TRACE_TSQL(STARTTIME)
	
IF NOT EXISTS(SELECT 1 FROM SYS.INDEXES WHERE NAME = 'IDX_NC_TRACETSQL_SQLCHECKSUM')
	CREATE NONCLUSTERED INDEX IDX_NC_TRACETSQL_SQLCHECKSUM ON DBO.TRACE_TSQL(SQLCHECKSUM)
GO

IF OBJECT_ID('DBO.COUNTERDATA','U') IS NULL
CREATE TABLE DBO.COUNTERDATA
(
	[GUID] [uniqueidentifier] NOT NULL,
	[CounterID] [int] NOT NULL,
	[RecordIndex] [int] NOT NULL,
	[CounterDateTime] [char](24) NOT NULL,
	[CounterValue] [float] NOT NULL,
	[FirstValueA] [int] NULL,
	[FirstValueB] [int] NULL,
	[SecondValueA] [int] NULL,
	[SecondValueB] [int] NULL,
	[MultiCount] [int] NULL,
	CONSTRAINT PK_COUNTERDATA_GUID_COUNTERID_RECORDINDEX PRIMARY KEY CLUSTERED ([GUID] ASC,[CounterID] ASC,[RecordIndex] ASC)
)
GO
IF NOT EXISTS(SELECT 1 FROM SYS.INDEXES WHERE NAME = 'IDX_NC_COUNTERDATA_COUNTERID_I_COUNTERDATETIME_COUNTERVALUE')
	CREATE NONCLUSTERED INDEX IDX_NC_COUNTERDATA_COUNTERID_I_COUNTERDATETIME_COUNTERVALUE ON DBO.COUNTERDATA(COUNTERID) INCLUDE(COUNTERDATETIME,COUNTERVALUE)
GO

--性能数据设置
IF OBJECT_ID('DBO.COUNTER_SETTING','U') IS NULL
CREATE TABLE DBO.COUNTER_SETTING
(
	NAME VARCHAR(100) NOT NULL,	
	VALUE INT NOT NULL				
)
GO

IF OBJECT_ID('DBO.COUNTERDETAILS','U') IS NULL
CREATE TABLE DBO.COUNTERDETAILS
(
	[CounterID] [int] IDENTITY(1,1) NOT NULL,
	[MachineName] [varchar](1024) NOT NULL,
	[ObjectName] [varchar](1024) NOT NULL,
	[CounterName] [varchar](1024) NOT NULL,
	[CounterType] [int] NOT NULL,
	[DefaultScale] [int] NOT NULL,
	[InstanceName] [varchar](1024) NULL,
	[InstanceIndex] [int] NULL,
	[ParentName] [varchar](1024) NULL,
	[ParentObjectID] [int] NULL,
	[TimeBaseA] [int] NULL,
	[TimeBaseB] [int] NULL,
	CONSTRAINT PK_COUNTERDETAILS PRIMARY KEY CLUSTERED (CounterID)
)
GO

IF OBJECT_ID('DBO.DISPLAYTOID','U') IS NULL
CREATE TABLE DBO.DISPLAYTOID
(
	[GUID] [uniqueidentifier] NOT NULL,
	[RunID] [int] NULL,
	[DisplayString] [varchar](1024) NOT NULL,
	[LogStartTime] [char](24) NULL,
	[LogStopTime] [char](24) NULL,
	[NumberOfRecords] [int] NULL,
	[MinutesToUTC] [int] NULL,
	[TimeZoneName] [char](32) NULL,
	CONSTRAINT PK_DISPLAYTOID PRIMARY KEY CLUSTERED ([GUID] ASC)
)
IF NOT EXISTS(SELECT 1 FROM SYS.INDEXES WHERE NAME = 'IDX_UQ_DISPLAYTOID_DISPLAYSTRING')
	CREATE UNIQUE INDEX IDX_UQ_DISPLAYTOID_DISPLAYSTRING ON DISPLAYTOID(DISPLAYSTRING)
GO

IF OBJECT_ID('DBO.MONITOR_FILTER_SETTING','U') IS NULL
CREATE TABLE DBO.MONITOR_FILTER_SETTING
(
	NAME VARCHAR(100) NOT NULL,
	VALUE INT NOT NULL
)
GO

USE [Monitor]
GO


IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[APP_SETTING]') AND type in (N'U'))
DROP TABLE [dbo].[APP_SETTING]
GO


IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MIRRORING_FILTER]') AND type in (N'U'))
DROP TABLE [dbo].[MIRRORING_FILTER]
GO

USE [Monitor]
GO


SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

SET ANSI_PADDING ON
GO

CREATE TABLE [dbo].[APP_SETTING](
	[APP] [varchar](100) NOT NULL,
 CONSTRAINT [PK_APP_SETTING] PRIMARY KEY CLUSTERED 
(
	[APP] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON) ON [PRIMARY]
) ON [PRIMARY]

GO

SET ANSI_PADDING OFF
GO

USE [Monitor]
GO

/****** Object:  Table [dbo].[MIRRORING_FILTER]    Script Date: 11/10/2021 14:25:56 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

SET ANSI_PADDING ON
GO

CREATE TABLE [dbo].[MIRRORING_FILTER](
	[NAME] [varchar](100) NOT NULL,
 CONSTRAINT [PK_MIRRORING_FILTER] PRIMARY KEY CLUSTERED 
(
	[NAME] ASC
)WITH (PAD_INDEX  = OFF, STATISTICS_NORECOMPUTE  = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS  = ON, ALLOW_PAGE_LOCKS  = ON) ON [PRIMARY]
) ON [PRIMARY]

GO

SET ANSI_PADDING OFF
GO


--****************************************** VIEW ****************************************
IF OBJECT_ID('DBO.PERFORMANCESLOG','V') IS NOT NULL
	DROP VIEW DBO.PERFORMANCESLOG
GO
CREATE VIEW DBO.PERFORMANCESLOG
AS
SELECT A.OBJECTNAME AS CATEGORYNAME,A.COUNTERNAME,A.INSTANCENAME,B.COUNTERVALUE AS NEXTVALUE,CAST(LEFT(B.COUNTERDATETIME,23) AS DATETIME) AS WRITETIME
FROM Monitor.DBO.COUNTERDETAILS A,Monitor.DBO.COUNTERDATA B
WHERE A.COUNTERID = B.COUNTERID
GO
IF OBJECT_ID('DBO.BACKUP_DBLIST','V') IS NOT NULL
	DROP VIEW DBO.BACKUP_DBLIST
GO
CREATE VIEW DBO.BACKUP_DBLIST
AS
	SELECT A.DATABASE_ID,A.NAME
	FROM SYS.DATABASES A
	WHERE A.DATABASE_ID > 4
		AND A.IS_READ_ONLY = 0
		AND A.IS_DISTRIBUTOR = 0
		AND A.STATE = 0
		AND A.NAME NOT LIKE '%AUTOREST'
		AND NOT EXISTS(SELECT 1 FROM DBO.BACKUP_FILTER B
			WHERE A.NAME = B.NAME)
GO

IF OBJECT_ID('DBO.CUSTOMER_DBLIST','V') IS NOT NULL
	DROP VIEW DBO.CUSTOMER_DBLIST
GO
CREATE VIEW DBO.CUSTOMER_DBLIST
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

--****************************************** SP ****************************************
IF OBJECT_ID('DBO.TOOL_GET_IPPORT','P') IS NOT NULL
	DROP PROC DBO.TOOL_GET_IPPORT
GO
CREATE PROC DBO.TOOL_GET_IPPORT
@IP	VARCHAR(50) OUTPUT,
@PORT VARCHAR(10) OUTPUT
AS
BEGIN
	DECLARE @LISTENONALLIPS INT
	DECLARE @REGEDITKEY VARCHAR(8000),@VERSIONKEY VARCHAR(100),@IPKEY VARCHAR(100) = 'IP1'
	IF @@VERSION LIKE 'Microsoft SQL Server 2021%'
		SET @VERSIONKEY = 'MSSQL16.'
	ELSE IF @@VERSION LIKE 'Microsoft SQL Server 2019%'
		SET @VERSIONKEY = 'MSSQL15.'
	ELSE IF @@VERSION LIKE 'Microsoft SQL Server 2017%'
		SET @VERSIONKEY = 'MSSQL14.'
	ELSE IF @@VERSION LIKE 'Microsoft SQL Server 2016%'
		SET @VERSIONKEY = 'MSSQL13.'
	ELSE IF @@VERSION LIKE 'Microsoft SQL Server 2014%'
		SET @VERSIONKEY = 'MSSQL12.'
	ELSE IF @@VERSION LIKE 'Microsoft SQL Server 2012%'
		SET @VERSIONKEY = 'MSSQL11.'
	ELSE IF @@VERSION LIKE 'Microsoft SQL Server 2008%'
		SET @VERSIONKEY = 'MSSQL10_50.'
	ELSE 
		RAISERROR('contact dba to find out the version of sqlserver and modify the sp:Monitor.dbo.TOOL_GET_IPPORT',11,1)

	SET @REGEDITKEY = 'SOFTWARE\Microsoft\Microsoft SQL Server\'+@VERSIONKEY+@@SERVICENAME+'\MSSQLServer\SuperSocketNetLib\Tcp'
	EXEC MASTER.DBO.XP_REGREAD @ROOTKEY = 'HKEY_LOCAL_MACHINE',@KEY = @REGEDITKEY,@VALUE_NAME = 'ListenOnAllIPs',@VALUE = @LISTENONALLIPS OUTPUT
	IF @LISTENONALLIPS = 0
	BEGIN
		SET @REGEDITKEY = 'SOFTWARE\Microsoft\Microsoft SQL Server\'+@VERSIONKEY+@@SERVICENAME+'\MSSQLServer\SuperSocketNetLib\Tcp\'+@IPKEY
		EXEC MASTER.DBO.XP_REGREAD @ROOTKEY = 'HKEY_LOCAL_MACHINE',@KEY = @REGEDITKEY,@VALUE_NAME = 'TcpPort',@VALUE = @PORT OUTPUT
		EXEC MASTER.DBO.XP_REGREAD @ROOTKEY = 'HKEY_LOCAL_MACHINE',@KEY = @REGEDITKEY,@VALUE_NAME = 'IpAddress',@VALUE = @IP OUTPUT
	END
	ELSE
	BEGIN
		--RAISERROR('IP1 IP,PORT NOT BANDING',10,1)
		SET @IPKEY = 'IPAll'
		SET @REGEDITKEY = 'SOFTWARE\Microsoft\Microsoft SQL Server\'+@VERSIONKEY+@@SERVICENAME+'\MSSQLServer\SuperSocketNetLib\Tcp\'+@IPKEY
		EXEC MASTER.DBO.XP_REGREAD @ROOTKEY = 'HKEY_LOCAL_MACHINE',@KEY = @REGEDITKEY,@VALUE_NAME = 'TcpPort',@VALUE = @PORT OUTPUT
		
		declare @tb_output TABLE
		(
		ip varchar(2000)
		)
		INSERT INTO @tb_output
		exec xp_cmdshell 'ipconfig /all' 

		select top 1 @ip=SUBSTRING(ip,CHARINDEX(':',ip)+2,1000)
		FROM @tb_output
		WHERE ip LIKE '%IP Address%' and (ip like '%: 11.%' or ip like '%: 30.%' or ip like '%: 9.%' or ip like '%: 172.%' or ip like '%: 10.%' or ip like '%: 100.%') and ip not like '%: 169.%'
		select @ip=left(@ip,DATALENGTH(@ip)-1)
		if (@ip is null) --win server 2008
		begin
			select top 1 @ip=SUBSTRING(ip,CHARINDEX(':',ip)+2,1000)
				FROM @tb_output
			WHERE ip LIKE '%IPv4 Address%' and (ip like '%: 11.%' or ip like '%: 30.%' or ip like '%: 9.%' or ip like '%: 172.%' or ip like '%: 10.%' or ip like '%: 100.%') and ip not like '%: 169.%'
			select @ip=left(@ip,DATALENGTH(@ip)-1)
			select @ip=SUBSTRING(@ip,0,CHARINDEX('(',@ip))
		end
	END
END
GO

-- =============================================
-- Description:	生成sqlserver服务器负载数据上报的xml
-- =============================================
IF OBJECT_ID('DBO.JOB_REPORT_LOAD','P') IS NOT NULL
	DROP PROC DBO.JOB_REPORT_LOAD
GO
CREATE PROCEDURE DBO.[JOB_REPORT_LOAD]
AS
BEGIN
	SET NOCOUNT ON;

	
	DECLARE @IP SYSNAME,@PORT SYSNAME,@CPU INT,@DISKUSEDPERCENT INT,@STATDATE VARCHAR(20),@IO DECIMAL(10,2),@TIMEMIN INT,
			@DATE CHAR(8),@DISKQUEUELENGTH DECIMAL(10,2),@USERCONNECTIONS BIGINT,@BATCHREQUESTS BIGINT,
			@SQLCOMPILATIONSSEC DECIMAL(10,2),@AVGDISKBYTESREAD DECIMAL(10,2),@AVGDISKBYTESWRITE DECIMAL(10,2),
			@FULLSACNSEC DECIMAL(10,2),@BUFFERCACHEHITRATIO INT,@SQLRECOMPILATIONSEC DECIMAL(10,2),
			@REQUESTSCOMPLETEDSEC INT,@CACHEHITRATIO DECIMAL(10,2),@SLOWQUERIES BIGINT,@CMD VARCHAR(4000)
	DECLARE @MONITOR_SERVICE_NAME VARCHAR(100)
	SET @MONITOR_SERVICE_NAME = CASE WHEN @@SERVICENAME = 'MSSQLSERVER' THEN 'SQLServer' ELSE @@SERVICENAME END
	--IP
	EXEC Monitor.DBO.TOOL_GET_IPPORT @IP OUT,@PORT OUT
	
	--DATE
	SELECT @STATDATE = convert(varchar,GETDATE(),120)
	SELECT @DATE = CONVERT(CHAR(8),GETDATE(),112),@TIMEMIN = DATEDIFF(MI,CONVERT(CHAR(8),GETDATE(),112),GETDATE())
	
	IF NOT EXISTS(select 1 from Monitor.DBO.PERFORMANCESLOG WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())) 
	AND EXISTS(select 1 from sys.dm_os_sys_info where sqlserver_start_time>'2021-11-10 09:00:00') AND @@SERVICENAME IN('MSSQLSERVER','S1')
	BEGIN
		SET @CMD='call D:\sql_install\dba_tools\Monitor\rebuildLogman.bat'
		EXEC XP_CMDSHELL @CMD
		SET @CMD='call D:\sql_install\dba_tools\Monitor\rebuildLogman.bat'
		EXEC XP_CMDSHELL @CMD
	END
	
	IF @MONITOR_SERVICE_NAME in('S1','SQLServer')
	BEGIN
		--CPU id_1001
		SELECT @CPU = ISNULL((CASE WHEN MAX(NEXTVALUE)> 100 THEN 100 ELSE CEILING(MAX(NEXTVALUE)) END),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME = 'Processor'
			AND COUNTERNAME = '% Processor Time'
			AND INSTANCENAME = '_Total'
			
		--磁盘IO负载 id_12947
		SELECT @IO = ISNULL((CASE WHEN MIN(NEXTVALUE)> 100 THEN 0 ELSE 100-CEILING(MIN(NEXTVALUE)) END),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME = 'LogicalDisk'
			AND COUNTERNAME = '% Idle Time'
			AND INSTANCENAME = 'D:'
			
		--磁盘等待队列 id_12952
		SELECT @DISKQUEUELENGTH = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME = 'LogicalDisk'
			AND COUNTERNAME = 'Avg. Disk Queue Length'
			AND INSTANCENAME = 'D:'
		
		--用户连接数 id_12951
		SELECT @USERCONNECTIONS = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':General Statistics'
			AND COUNTERNAME = 'User Connections'

		--请求数 id_12948
		SELECT @BATCHREQUESTS = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':SQL Statistics'
			AND COUNTERNAME = 'Batch Requests/sec'
			
		--SQL_Compilations/sec id_12968
		SELECT @SQLCOMPILATIONSSEC = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':SQL Statistics'
			AND COUNTERNAME = 'SQL Compilations/sec'
		

		--	Avg_Disk_Bytes/Read	0	id_12955
		SELECT @AVGDISKBYTESREAD = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME = 'LogicalDisk'
			AND COUNTERNAME = 'Avg. Disk Bytes/Read'
			AND INSTANCENAME = 'D:'
			
		--	Avg_Disk_Bytes/Write（平均读写）	0	id_12956
		SELECT @AVGDISKBYTESWRITE = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME = 'LogicalDisk'
			AND COUNTERNAME = 'Avg. Disk Bytes/Write'
			AND INSTANCENAME = 'D:'
			
		--Full_Scans/sec（全表扫描）	0	id_12958
		SELECT @FULLSACNSEC = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':Access Methods'
			AND COUNTERNAME = 'Full Scans/sec'
			
		--Buffer_cache_hit_ratio（高速缓存查	0	id_12949
		SELECT @BUFFERCACHEHITRATIO = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':Buffer Manager'
			AND COUNTERNAME = 'Buffer cache hit ratio'
			
		--SQL_Re-Compilations/sec	0	id_12950
		SELECT @SQLRECOMPILATIONSEC = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':SQL Statistics'
			AND COUNTERNAME = 'SQL Re-Compilations/sec'
			
		--Requests_completed/sec	0	id_12967
		SELECT @REQUESTSCOMPLETEDSEC = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':Workload Group Stats'
			AND COUNTERNAME = 'Requests completed/sec'
			
		--Cache_Hit_Ratio	0	id_12965
		SELECT @CACHEHITRATIO = ISNULL(MAX(NEXTVALUE),0)
		FROM Monitor.DBO.PERFORMANCESLOG
		WHERE WRITETIME >= DATEADD(SS,-59,GETDATE())
			AND CATEGORYNAME LIKE '%'+@MONITOR_SERVICE_NAME+':Plan Cache'
			AND COUNTERNAME = 'Cache Hit Ratio'
		
		--DISK USED PERCENT 0 id_874095
		IF OBJECT_ID('TEMPDB.DBO.#DISKTOTALSIZE','U') IS NOT NULL
			DROP TABLE #DISKTOTALSIZE
		IF OBJECT_ID('TEMPDB.DBO.#DISKFREESIZE','U') IS NOT NULL
			DROP TABLE #DISKFREESIZE
		CREATE TABLE #DISKTOTALSIZE(INDEXNO INT IDENTITY,SIZEKB NVARCHAR(100))
		INSERT INTO #DISKTOTALSIZE EXEC MASTER.DBO.XP_CMDSHELL 'WMIC LOGICALDISK WHERE NAME=''D:'' GET SIZE'
		CREATE TABLE #DISKFREESIZE(NAME VARCHAR(10),FREESIZEMB INT)
		INSERT INTO #DISKFREESIZE EXEC MASTER.DBO.XP_FIXEDDRIVES;
		
		--部分旧服务器无法使用WMIC(老A5统一计算为680GB)
		IF NOT EXISTS(SELECT 1  FROM #DISKTOTALSIZE WHERE INDEXNO = 2 AND ISNUMERIC(LEFT(SIZEKB,LEN(SIZEKB)-1)) = 1)
			SET @DISKUSEDPERCENT =CEILING(100*(680-(SELECT FREESIZEMB/1024.0 FROM #DISKFREESIZE WHERE NAME = 'D'))/680)
		ELSE 
			SELECT @DISKUSEDPERCENT = CEILING(100*(SELECT CAST(LEFT(SIZEKB,LEN(SIZEKB)-1) AS BIGINT)/1024.0/1024/1024-(SELECT FREESIZEMB/1024.0 FROM #DISKFREESIZE WHERE NAME = 'D') FROM #DISKTOTALSIZE WHERE INDEXNO = 2)/(SELECT CAST(LEFT(SIZEKB,LEN(SIZEKB)-1) AS BIGINT)/1024.0/1024/1024 FROM #DISKTOTALSIZE WHERE INDEXNO = 2))

			
		--mssql_slow_queries	0	id_12970
		IF OBJECT_ID('DBO.TRACE_TSQL','U') IS NULL
			SET @SLOWQUERIES = 0
		ELSE 
			SELECT @SLOWQUERIES = COUNT(1)
			FROM Monitor.DBO.TRACE_TSQL
			WHERE STARTTIME >= DATEADD(SS,-59,GETDATE())
				AND DATABASENAME <> 'Monitor'
				AND ISNULL(APPLICATIONNAME,'') NOT LIKE 'SQLAgent%'
				AND ISNULL(APPLICATIONNAME,'') <> 'SQLCMD'
		
		SET @CMD = 'echo ^<?xml version=''1.0'' encoding="iso-8859-1" ?^> >d:\dbbak\mssql_spes_new.xml'							EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_data name="mssql_spes_new"^> >>d:\dbbak\mssql_spes_new.xml'										EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_row^> >>d:\dbbak\mssql_spes_new.xml'																EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="ip"^>'+isnull(@IP,'127.0.0.1')+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'							EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="port"^>'+isnull(@PORT,'48322')+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'							EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="report_day"^>'+LTRIM(isnull(@DATE,'20220816'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'			EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="time_min"^>'+LTRIM(isnull(@TIMEMIN,'863'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'			EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_1001"^>'+LTRIM(isnull(@CPU,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'				EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12947"^>'+LTRIM(isnull(@IO,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'				EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12952"^>'+LTRIM(isnull(@DISKQUEUELENGTH,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'	EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12951"^>'+LTRIM(isnull(@USERCONNECTIONS,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'	EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12948"^>'+LTRIM(isnull(@BATCHREQUESTS,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'	EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12968"^>'+LTRIM(isnull(@SQLCOMPILATIONSSEC,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12955"^>'+LTRIM(isnull(@AVGDISKBYTESREAD,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12956"^>'+LTRIM(isnull(@AVGDISKBYTESWRITE,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD		
		SET @CMD = 'echo ^<xml_field name="id_12958"^>'+LTRIM(isnull(@FULLSACNSEC,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'				EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12949"^>'+LTRIM(isnull(@BUFFERCACHEHITRATIO,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12950"^>'+LTRIM(isnull(@SQLRECOMPILATIONSEC,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12967"^>'+LTRIM(isnull(@REQUESTSCOMPLETEDSEC,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'	EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12965"^>'+LTRIM(isnull(@CACHEHITRATIO,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'			EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_874095"^>'+LTRIM(isnull(@DISKUSEDPERCENT,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="id_12970"^>'+LTRIM(isnull(@SLOWQUERIES,'0'))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_field name="add_time"^>'+LTRIM(isnull(@STATDATE,''))+'^</xml_field^>	>>d:\dbbak\mssql_spes_new.xml'		EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^</xml_row^>	>>d:\dbbak\mssql_spes_new.xml'															EXEC MASTER.DBO.XP_CMDSHELL @CMD
		SET @CMD = 'echo ^</xml_data^>	>>d:\dbbak\mssql_spes_new.xml'															EXEC MASTER.DBO.XP_CMDSHELL @CMD
		
		--SEND
		--SET @CMD='cd d:\dbbak && d: && d:\perl\bin\perl.exe send_xml.pl -c mssql_spes_new.xml -t 60'
		SET @CMD='cd d:\dbbak && d: && C:\cygwinroot\bin\sh.exe send_xml.sh mssql_spes_new mssql_spes_new.xml'
		EXEC MASTER.DBO.XP_CMDSHELL @CMD
	END
	
	--DELETE OLD DATA
	DECLARE @KEEPDATADAYS INT
	SELECT @KEEPDATADAYS = VALUE FROM DBO.COUNTER_SETTING WHERE NAME = 'KEEP_DATA_DAYS'
	DELETE DBO.COUNTERDATA WHERE LEFT(COUNTERDATETIME,23) < CONVERT(CHAR(23),GETDATE()-@KEEPDATADAYS,121)
END

GO

 
-- =============================================
-- AUTHOR:		<cainhe 贺陆军>
-- CREATE DATE: <2010/07/01>
-- DESCRIPTION:	<代理执行:每5分钟,加载数据到Monitor内>
-- EXEC Monitor.DBO.JOB_TRACE 1
-- 查看当前活动的跟踪:SELECT * FROM DBO.TRACE_CURRENT_TRACEINFO
-- 查看当前跟踪的数据:SELECT * FROM FN_TRACE_GETTABLE(@TRACEFILE,DEFAULT)
-- =============================================
IF OBJECT_ID('DBO.JOB_TRACE','P') IS NOT NULL
	DROP PROC DBO.JOB_TRACE
GO
CREATE PROCEDURE DBO.JOB_TRACE
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
		SELECT @FILTERDURATION = VALUE*1000000 FROM DBO.TRACE_SETTING WHERE NAME = 'FILTER_DURATION'
		SELECT @KEEPDATADAYS = VALUE FROM DBO.TRACE_SETTING WHERE NAME = 'KEEP_DATA_DAYS'
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


-- =============================================
--功能:DB故障进行验证并切换到DR
--不能切换的场景:
--1.DB待发送日志大于10MB
--2.DR待重做日志大于1MB
--切换方式:
--USE MASTER ALTER DATABASE DBNAME SET PARTNER FORCE_SERVICE_ALLOW_DATA_LOSS;
--检测镜像是否都切换为主
-- =============================================
IF OBJECT_ID('DBO.TOOL_DR2DB','P') IS NOT NULL
	DROP PROC DBO.TOOL_DR2DB
GO
CREATE PROCEDURE DBO.TOOL_DR2DB
AS
BEGIN

	SET NOCOUNT ON;
	DECLARE @SQL VARCHAR(MAX),@PORT VARCHAR(100)
	

	BEGIN TRY
	--获取多实例的端口
		EXEC Monitor.DBO.TOOL_GET_IPPORT NULL,@PORT OUT
		IF @PORT IS NULL
			RAISERROR(N'GAMEDR SWITCH ERROR',11,1);
		
    --不能切换的场景
		--1.DB待发送日志大于10MB
		IF EXISTS(SELECT 1 FROM SYS.DM_OS_PERFORMANCE_COUNTERS
		WHERE OBJECT_NAME LIKE '%Database Mirroring%' 
			AND COUNTER_NAME = 'Log Send Queue KB' 
			AND CNTR_VALUE > 10240)
		BEGIN
			SELECT -1 AS STATUS,'GAMEDB LOG SEND QUEUE MORE THAN 10MB' AS MSG
			RETURN -1
		END
		
		--2.DR待重做日志大于1MB
		IF EXISTS(SELECT 1 FROM SYS.DM_OS_PERFORMANCE_COUNTERS
		WHERE OBJECT_NAME LIKE '%Database Mirroring%' 
			AND COUNTER_NAME = 'Redo Queue KB' 
			AND CNTR_VALUE > 1024)
		BEGIN
			SELECT -1 AS STATUS,'GAMEDR REDO QUEUE MORE THAN 1MB' AS MSG
			RETURN -1
		END
		
		--记录需要切换的数据库
		IF OBJECT_ID('TEMPDB.DBO.#DBLIST','U') IS NOT NULL
			DROP TABLE #DBLIST
		SELECT A.NAME INTO #DBLIST
		FROM SYS.DATABASES A,SYS.DATABASE_MIRRORING B
		WHERE A.DATABASE_ID = B.DATABASE_ID
			AND A.DATABASE_ID > 4
			AND A.NAME <> 'Monitor'
			AND B.MIRRORING_ROLE = 2
			AND B.MIRRORING_STATE IS NOT NULL
			
    --切换
		--1.DR断开/删除ENDPOINT
		IF EXISTS(SELECT 1 FROM SYS.ENDPOINTS WHERE NAME = N'endpoint_mirroring') 
			DROP ENDPOINT endpoint_mirroring
		--2.DR切换
		SET @SQL = NULL
		SELECT @SQL=ISNULL(@SQL+'','')+'ALTER DATABASE ['+NAME+'] SET PARTNER FORCE_SERVICE_ALLOW_DATA_LOSS;'
		FROM #DBLIST
		--PRINT(@SQL)
		EXEC(@SQL)
		--3.重新建立ENDPOINT
		SET @SQL = 'CREATE ENDPOINT endpoint_mirroring STATE = STARTED AS TCP ( LISTENER_PORT = '+LTRIM(37022+RIGHT(@PORT/10,1)-2)+' ) FOR DATABASE_MIRRORING (ROLE=PARTNER);'
		--PRINT(@SQL)
		EXEC(@SQL)
		
	--检查镜像是否都切换为主
	IF EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING WHERE MIRRORING_ROLE = 2)
		RAISERROR(N'gamedr switch failed',11,1);
	
	SELECT 1 AS STATUS,'gamedr switch success' AS MSG
	END TRY
	
	BEGIN CATCH
		SELECT -1 AS STATUS,'gamedr switch exception' AS MSG
	END CATCH
	
END
GO


-- =============================================
-- Description:	业务公用-生成镜像数据库快照
-- =============================================
IF OBJECT_ID('DBO.JOB_SNAPSHOT','P') IS NOT NULL
	DROP PROC DBO.JOB_SNAPSHOT
GO
CREATE PROCEDURE DBO.JOB_SNAPSHOT
AS
BEGIN

	SET NOCOUNT ON
	
	declare @dbid int,@db sysname,@dr sysname, @logic sysname,@has_monitor tinyint,@msg varchar(2000),@cmd varchar(max),@cmd2 varchar(max)

	declare @port sysname
	exec monitor.dbo.TOOL_GET_IPPORT null,@port output

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

-- =============================================
-- Description:	自动部署服务器的复制监控
-- =============================================
IF OBJECT_ID('DBO.TOOL_DEPLOY_REPL_MONITOR','P') IS NOT NULL
	DROP PROC DBO.TOOL_DEPLOY_REPL_MONITOR
GO
CREATE PROCEDURE DBO.TOOL_DEPLOY_REPL_MONITOR
AS
BEGIN
	SET NOCOUNT ON

	DECLARE @SQL VARCHAR(MAX)
	SELECT @SQL = ISNULL(@SQL+'
	','')+'
	USE MSDB
	DECLARE @JOBNAME'+UPPER(NAME)+' VARCHAR(2000)=''TC_REPL_MONITOR_'+UPPER(NAME)+'''
	IF EXISTS(SELECT 1 FROM MSDB.DBO.SYSJOBS WHERE NAME=@JOBNAME'+UPPER(NAME)+')
	BEGIN
		EXEC MSDB.DBO.SP_DELETE_JOB @job_name=@JOBNAME'+UPPER(NAME)+',@delete_unused_schedule=1
	END

	USE ['+A.NAME+']
	IF OBJECT_ID(''DBO.TC_REPL_CHECK_LOG'',''U'') IS NULL
		CREATE TABLE DBO.TC_REPL_CHECK_LOG
		(
		WRITETIME DATETIME NULL,
		[TYPE] INT NULL
		)

	DECLARE @SQLINSIDE'+UPPER(NAME)+' VARCHAR(MAX)
	SET @SQLINSIDE'+UPPER(NAME)+'=
	CASE WHEN OBJECT_ID(''DBO.TC_JOB_REPL_MONITOR'',''P'') IS NOT NULL THEN ''ALTER'' ELSE ''CREATE'' END+'' PROC [DBO].[TC_JOB_REPL_MONITOR]
		@PUB SYSNAME = '''''+A.NAME+''''',
		@MAXLATENCYSECONDS INT = 15
	AS
	BEGIN
		SET NOCOUNT ON
		
		IF NOT EXISTS(SELECT 1 FROM SYS.DATABASES WHERE IS_PUBLISHED = 1 AND NAME = '''''+A.NAME+''''')
			RETURN
		
		SET XACT_ABORT ON
		DECLARE @MESSAGE VARCHAR(8000)
		DECLARE @DOS_CMD VARCHAR(8000)
		
		DECLARE @IP VARCHAR(100),@PORT VARCHAR(100),@APPCODE VARCHAR(100)
		EXEC MONITOR.DBO.TOOL_GET_IPPORT @IP OUTPUT,@PORT OUTPUT
		SELECT @APPCODE = APP FROM Monitor.DBO.BACKUP_SETTING
		
		IF OBJECT_ID('''''+A.NAME+'.DBO.TC_REPL_LATENCY_STATS'''') IS NULL
			CREATE TABLE '+A.NAME+'.DBO.TC_REPL_LATENCY_STATS
				( 
					DISTRIBUTOR_LATENCY INT NULL,
					SUBSCRIBER VARCHAR(1000) NULL,
					SUBSCRIBER_DB VARCHAR(1000) NULL,
					SUBSCRIBER_LATENCY INT NULL,
					OVERALL_LATENCY INT NULL 
				)
		TRUNCATE TABLE '+A.NAME+'.DBO.TC_REPL_LATENCY_STATS
		
		DECLARE @TOKENHANDLE BIGINT
		EXEC SP_POSTTRACERTOKEN @PUBLICATION = @PUB,@TRACER_TOKEN_ID = @TOKENHANDLE OUTPUT;

		IF @TOKENHANDLE IS NULL OR @@ERROR<>0
		BEGIN
			INSERT INTO '+A.NAME+'.DBO.TC_REPL_CHECK_LOG VALUES(GETDATE(),1)
			IF EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=1 GROUP BY TYPE HAVING COUNT(1)>=5)
			BEGIN
				DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=1
				INSERT INTO OPENROWSET(''''SQLNCLI'''','''''+B.IP+','+B.PORT+''''';'''''+B.ACCOUNT+''''';'''''+B.PWD+''''','+B.DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
				SELECT @APPCODE,@IP,@PORT,''''REPL_TOKEN'''',1
			END
			RETURN -1
		END
		ELSE
		BEGIN
			DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=1
		END
		
		DECLARE @MAXWAIT INT = @MAXLATENCYSECONDS * 2;
		IF @MAXWAIT > 30
		BEGIN
			SET @MAXWAIT = 30;
		END
		DECLARE @WAITFOR VARCHAR(10) = ''''00:00:'''' + CAST((@MAXWAIT) AS VARCHAR(2));
		WAITFOR DELAY @WAITFOR;

		INSERT '+A.NAME+'.DBO.TC_REPL_LATENCY_STATS (DISTRIBUTOR_LATENCY,SUBSCRIBER,SUBSCRIBER_DB,SUBSCRIBER_LATENCY,OVERALL_LATENCY)
		EXEC SP_HELPTRACERTOKENHISTORY @PUB,@TOKENHANDLE;
		
		IF @@ROWCOUNT=0 OR @@ERROR<>0
		BEGIN
			INSERT INTO '+A.NAME+'.DBO.TC_REPL_CHECK_LOG VALUES(GETDATE(),2)
			IF EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=2 GROUP BY TYPE HAVING COUNT(1)>=5)
			BEGIN
				DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=2
				INSERT INTO OPENROWSET(''''SQLNCLI'''','''''+B.IP+','+B.PORT+''''';'''''+B.ACCOUNT+''''';'''''+B.PWD+''''','+B.DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
				SELECT @APPCODE,@IP,@PORT,''''REPL_TOKEN'''',1
			END
			RETURN -1
		END
		ELSE
		BEGIN
			DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=2
		END

		DECLARE @CUTOFF DATETIME = GETDATE();
		EXEC SP_DELETETRACERTOKENHISTORY @PUBLICATION = @PUB,@CUTOFF_DATE = @CUTOFF;

		IF EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_LATENCY_STATS WHERE OVERALL_LATENCY IS NULL) OR NOT EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_LATENCY_STATS)
		BEGIN
			INSERT INTO '+A.NAME+'.DBO.TC_REPL_CHECK_LOG VALUES(GETDATE(),3)
			IF (EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=3 GROUP BY TYPE HAVING COUNT(1)>=5))
			BEGIN
				DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=3
				INSERT INTO OPENROWSET(''''SQLNCLI'''','''''+B.IP+','+B.PORT+''''';'''''+B.ACCOUNT+''''';'''''+B.PWD+''''','+B.DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
				SELECT @APPCODE,@IP,@PORT,''''REPL_SEND_LOG'''',1
			END
			RETURN -1
		END
		ELSE
		BEGIN
			DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=3
		END
		
		IF EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_LATENCY_STATS WHERE OVERALL_LATENCY > @MAXLATENCYSECONDS)
		BEGIN		
			INSERT INTO '+A.NAME+'.DBO.TC_REPL_CHECK_LOG VALUES(GETDATE(),5)
			
			IF (EXISTS(SELECT 1 FROM '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=5 GROUP BY TYPE HAVING COUNT(1)>=5))
			BEGIN
				DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=5
				INSERT INTO OPENROWSET(''''SQLNCLI'''','''''+B.IP+','+B.PORT+''''';'''''+B.ACCOUNT+''''';'''''+B.PWD+''''','+B.DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
				SELECT @APPCODE,@IP,@PORT,''''REPL_LATENCY'''',1
				RETURN -1
			END
		END
		ELSE
		BEGIN
			DELETE '+A.NAME+'.DBO.TC_REPL_CHECK_LOG WHERE TYPE=5
		END
	END'';
	EXEC(@SQLINSIDE'+UPPER(NAME)+')

	USE MSDB
	DECLARE @jobId'+UPPER(NAME)+' BINARY(16)

	DECLARE @SERVERNAME'+UPPER(NAME)+' VARCHAR(2000)=CAST(SERVERPROPERTY(''SERVERNAME'') AS SYSNAME)
	DECLARE @SCHEDULENAME'+UPPER(NAME)+' VARCHAR(2000)=''REPLCHECK_'+UPPER(NAME)+'''
	DECLARE @CMD'+UPPER(NAME)+' VARCHAR(2000)=''EXEC DBO.TC_JOB_REPL_MONITOR''
	DECLARE @STEPNAME'+UPPER(NAME)+' VARCHAR(2000)=''REPLCHECK_'+UPPER(NAME)+'''
	DECLARE @DBNAME'+UPPER(NAME)+' VARCHAR(2000)='''+UPPER(NAME)+'''

	EXEC  msdb.dbo.sp_add_job @job_name=@JOBNAME'+UPPER(NAME)+',
			@enabled=1,
			@notify_level_eventlog=0,
			@notify_level_email=2,
			@notify_level_netsend=2,
			@notify_level_page=2,
			@delete_level=0,
			@category_name=N''[Uncategorized (Local)]'',
			@owner_login_name=''sa'',@job_id = @jobId'+UPPER(NAME)+' OUTPUT
	EXEC msdb.dbo.sp_add_jobserver @job_name=@JOBNAME'+UPPER(NAME)+',@server_name = @SERVERNAME'+UPPER(NAME)+'
	EXEC msdb.dbo.sp_add_jobstep @job_name=@JOBNAME'+UPPER(NAME)+',@step_name=@STEPNAME'+UPPER(NAME)+',
			@step_id=1,
			@cmdexec_success_code=0,
			@on_success_action=1,
			@on_fail_action=2,
			@retry_attempts=0,
			@retry_interval=0,
			@os_run_priority=0,@subsystem=N''TSQL'',
			@command=@CMD'+UPPER(NAME)+',
			@database_name=@DBNAME'+UPPER(NAME)+',
			@flags=0
	EXEC msdb.dbo.sp_update_job @job_name=@JOBNAME'+UPPER(NAME)+',
			@enabled=1,
			@start_step_id=1,
			@notify_level_eventlog=0,
			@notify_level_email=2,
			@notify_level_netsend=2,
			@notify_level_page=2,
			@delete_level=0,
			@description=N'''',
			@category_name=N''[Uncategorized (Local)]'',
			@owner_login_name=''sa'',
			@notify_email_operator_name=N'''',
			@notify_netsend_operator_name=N'''',
			@notify_page_operator_name=N''''
	DECLARE @schedule_id'+UPPER(NAME)+' int
	EXEC msdb.dbo.sp_add_jobschedule @job_name=@JOBNAME'+UPPER(NAME)+',@name=@SCHEDULENAME'+UPPER(NAME)+',
	@enabled=1,
			@freq_type=4,
			@freq_interval=1,
			@freq_subday_type=4,
			@freq_subday_interval=1,
			@freq_relative_interval=0,
			@freq_recurrence_factor=0,
			@active_start_date=20130509,
			@active_end_date=99991231,
			@active_start_time=0,
			@active_end_time=235959,
			@schedule_id = @schedule_id'+UPPER(NAME)+' OUTPUT
	SELECT @jobId'+UPPER(NAME)+' AS JOBID,@schedule_id'+UPPER(NAME)+' AS SCHEDULE_ID;'
	FROM SYS.DATABASES A,MONITOR.DBO.MONITOR_SERVER_SETTING B
	WHERE A.DATABASE_ID > 4
		AND A.STATE = 0
		AND A.IS_READ_ONLY = 0
		AND A.IS_DISTRIBUTOR = 0
		AND A.IS_PUBLISHED = 1
		AND B.STATE = 1
	--PRINT(@SQL)
	EXEC(@SQL)
END
GO

IF OBJECT_ID('DBO.TOOL_DEPLOY_SNAPSHOT','P') IS NOT NULL
	DROP PROC DBO.TOOL_DEPLOY_SNAPSHOT
GO
CREATE PROCEDURE DBO.TOOL_DEPLOY_SNAPSHOT
@JOBNAME VARCHAR(100) = 'TC_SNAPSHOT',
@JOBSTARTTIME INT = 0
AS
BEGIN
	SET NOCOUNT ON;

    DECLARE @jobId BINARY(16)

	DECLARE @SERVERNAME VARCHAR(2000)
	DECLARE @STEPNAME VARCHAR(2000),@DBNAME VARCHAR(2000)
	DECLARE @SCHEDULENAME VARCHAR(2000),@CMD VARCHAR(2000)

	SELECT @CMD='EXEC MONITOR.DBO.JOB_SNAPSHOT'

	SELECT @STEPNAME=@JOBNAME+'_1',
		@SCHEDULENAME=@JOBNAME+'_1',
		@DBNAME='MASTER',
		@SERVERNAME=CAST(SERVERPROPERTY('SERVERNAME') AS SYSNAME)

	IF EXISTS(SELECT 1 FROM MSDB.dbo.sysjobs WHERE NAME=@JOBNAME)
	BEGIN
		EXEC msdb.dbo.sp_delete_job @job_name=@JOBNAME,@delete_unused_schedule=1
	END
	EXEC  msdb.dbo.sp_add_job @job_name=@JOBNAME,
			@enabled=1,
			@notify_level_eventlog=0,
			@notify_level_email=2,
			@notify_level_netsend=2,
			@notify_level_page=2,
			@delete_level=0,
			@category_name=N'[Uncategorized (Local)]',
			@owner_login_name='sa',@job_id = @jobId OUTPUT

	EXEC msdb.dbo.sp_add_jobserver @job_name=@JOBNAME,@server_name = @SERVERNAME

	EXEC msdb.dbo.sp_add_jobstep @job_name=@JOBNAME,@step_name=@STEPNAME,
			@step_id=1,
			@cmdexec_success_code=0,
			@on_success_action=1,
			@on_fail_action=2,
			@retry_attempts=0,
			@retry_interval=0,
			@os_run_priority=0,@subsystem=N'TSQL',
			@command=@CMD,
			@database_name=@DBNAME,
			@flags=0
	EXEC msdb.dbo.sp_update_job @job_name=@JOBNAME,
			@enabled=1,
			@start_step_id=1,
			@notify_level_eventlog=0,
			@notify_level_email=2,
			@notify_level_netsend=2,
			@notify_level_page=2,
			@delete_level=0,
			@description=N'',
			@category_name=N'[Uncategorized (Local)]',
			@owner_login_name='sa',
			@notify_email_operator_name=N'',
			@notify_netsend_operator_name=N'',
			@notify_page_operator_name=N''
	DECLARE @schedule_id int
	EXEC msdb.dbo.sp_add_jobschedule @job_name=@JOBNAME,@name=@SCHEDULENAME,
			@enabled=1,
			@freq_type=4,
			@freq_interval=1,
			@freq_subday_type=1,
			@freq_subday_interval=0,
			@freq_relative_interval=0,
			@freq_recurrence_factor=1,
			@active_start_date=20130723,
			@active_end_date=99991231,
			@active_start_time=@JOBSTARTTIME,
			@active_end_time=235959,@schedule_id = @schedule_id OUTPUT
	SELECT @jobId AS JOBID,@schedule_id AS SCHEDULE_ID
END
GO

IF OBJECT_ID('DBO.JOB_MONITOR_FILTER','P') IS NOT NULL
	DROP PROC DBO.JOB_MONITOR_FILTER
GO
CREATE PROC DBO.JOB_MONITOR_FILTER
WITH RECOMPILE
AS
BEGIN
	SET NOCOUNT ON
	DECLARE @APPCODE VARCHAR(100),@CONNECT_FAIL_TIMES INT

	--UPLOAD DATA
	DECLARE @IP VARCHAR(20),@PORT VARCHAR(20),@SQL VARCHAR(MAX)
	EXEC MONITOR.DBO.TOOL_GET_IPPORT @IP OUTPUT,@PORT OUTPUT
	
	SELECT @APPCODE = APP FROM DBO.BACKUP_SETTING
	SELECT @CONNECT_FAIL_TIMES = COUNT(1) 
	FROM DBO.MONITOR_SERVER_UNAVAILABLE_HISTORY A,DBO.MONITOR_SERVER_SETTING B
	WHERE A.WRITETIME >= DATEADD(MI,-3,GETDATE())
		AND A.IP = B.IP AND A.PORT = B.PORT AND A.DBNAME = B.DBNAME AND A.PWD = B.PWD
		AND B.[STATE] = 1
	IF @CONNECT_FAIL_TIMES >= 2
	BEGIN
		UPDATE DBO.MONITOR_SERVER_SETTING SET [STATE] = [STATE]^1
	END
	
	IF EXISTS(SELECT 1 FROM [Monitor].[dbo].[BACKUP_SETTING] where APP in(SELECT APP FROM MONITOR.DBO.APP_SETTING))
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
	
	IF EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING where mirroring_safety_level=2)
	BEGIN
		SELECT @SQL = ISNULL(@SQL+'','')+'ALTER DATABASE ['+b.name+'] SET SAFETY OFF;'
		FROM SYS.DATABASE_MIRRORING a left join sys.databases b on a.database_id=b.database_id
		where mirroring_safety_level=2
		EXEC(@SQL)
	END
	
	/*
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
		FROM MASTER.SYS.DM_OS_PERFORMANCE_COUNTERS A,monitor.DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = 'MIRRORING_LOG_SEND_QUEUE_KB'
				AND A.OBJECT_NAME LIKE '%DATABASE MIRRORING%'
				AND A.COUNTER_NAME='LOG SEND QUEUE KB'
			AND A.INSTANCE_NAME != '_TOTAL'
				AND A.CNTR_VALUE > B.VALUE*10
				AND EXISTS(SELECT 1 FROM MASTER.SYS.DATABASE_MIRRORING C WHERE C.MIRRORING_ROLE = 1)
		)

		AND A.DATABASE_ID = B.DATABASE_ID
		AND B.TYPE = 1
		-- print(@SQL)
		EXEC(@SQL)
	
		SET @SQL = NULL
		SELECT @SQL = '
		--SERVICE_AVAILABLE
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.INSTANCE_AVAILABLE_HISTORY)(APPCODE,IP,PORT) VALUES('''+@APPCODE+''','''+@IP+''','+@PORT+')
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		--DISK_D_FREE_MB
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.NEXTVALUE
		FROM DBO.PERFORMANCESLOG A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''DISK_D_FREE_MB''
			AND A.CATEGORYNAME = ''LOGICALDISK''
			AND A.INSTANCENAME = ''D:''
			AND A.COUNTERNAME = ''Free Megabytes''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE())
			AND A.NEXTVALUE < B.VALUE
		UNION ALL
		--DISK_C_FREE_MB
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.NEXTVALUE
		FROM DBO.PERFORMANCESLOG A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''DISK_C_FREE_MB''
			AND A.CATEGORYNAME = ''LOGICALDISK''
			AND A.INSTANCENAME = ''C:''
			AND A.COUNTERNAME = ''Free Megabytes''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE())
			AND A.NEXTVALUE < B.VALUE
		UNION ALL
		--CPU_USE_PERCENT
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.NEXTVALUE
		FROM DBO.PERFORMANCESLOG A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''CPU_USE_PERCENT''
			AND A.CATEGORYNAME = ''PROCESSOR''
			AND A.COUNTERNAME = ''% Processor Time''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE())
			AND A.NEXTVALUE > B.VALUE
		UNION ALL
		--IO_IDLE_PERCENT
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.NEXTVALUE
		FROM DBO.PERFORMANCESLOG A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''IO_IDLE_PERCENT''
			AND A.CATEGORYNAME = ''LogicalDisk''
			AND A.INSTANCENAME = ''D:''
			AND A.COUNTERNAME = ''% Idle Time''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE())
			AND A.NEXTVALUE < B.VALUE
			AND EXISTS(SELECT 1 FROM DBO.BACKUP_DBLIST)
			AND NOT EXISTS(SELECT 1 FROM SYS.DM_EXEC_REQUESTS WHERE COMMAND LIKE ''BACKUP%'')
		UNION ALL
		--MEMORY_FREE_MB
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.NEXTVALUE
		FROM DBO.PERFORMANCESLOG A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''MEMORY_FREE_MB''
			AND A.CATEGORYNAME = ''Memory''
			AND A.COUNTERNAME = ''Available MBytes''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE())
			AND A.NEXTVALUE < B.VALUE
		UNION ALL
		--MIRRORING_LOG_SEND_QUEUE_KB
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.CNTR_VALUE
		FROM MASTER.SYS.DM_OS_PERFORMANCE_COUNTERS A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''MIRRORING_LOG_SEND_QUEUE_KB''
			AND A.OBJECT_NAME LIKE ''%DATABASE MIRRORING%''
			AND A.COUNTER_NAME=''LOG SEND QUEUE KB''
			AND A.INSTANCE_NAME != ''_TOTAL''
			AND A.CNTR_VALUE > B.VALUE*10
			AND EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING C WHERE C.MIRRORING_ROLE = 1)
		UNION ALL
		--USER_CONNECTION_NUMBER
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,A.NEXTVALUE
		FROM DBO.PERFORMANCESLOG A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''USER_CONNECTION_NUMBER''
			AND A.CATEGORYNAME LIKE ''%General Statistics''
			AND A.COUNTERNAME = ''User Connections''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE())
			AND A.NEXTVALUE > B.VALUE
		UNION ALL
		--SLOW_QUERY_IN_5MI
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',B.NAME,COUNT(1)
		FROM MONITOR.DBO.TRACE_TSQL A,DBO.MONITOR_FILTER_SETTING B
		WHERE B.NAME = ''SLOW_QUERY_IN_5MI''
			AND A.STARTTIME >= DATEADD(MI,-1*B.VALUE,GETDATE())
			AND A.DATABASENAME <> ''MONITOR''
			AND ISNULL(A.APPLICATIONNAME,'''') NOT LIKE ''SQLAgent%''
			AND ISNULL(A.APPLICATIONNAME,'''') <> ''SQLCMD''
			AND A.LOGINNAME NOT IN( ''sa'',''distributor_admin'')
			AND A.LOGINNAME NOT LIKE ''%\sqlserver''
		GROUP BY B.NAME
		HAVING COUNT(1) > 0'
		FROM DBO.MONITOR_SERVER_SETTING
		WHERE [STATE] = 1
		--PRINT(@SQL)
		EXEC(@SQL)
		
		
		SET @SQL = NULL
		SELECT @SQL = '
		--MIRRORING_STATUS
		IF EXISTS(SELECT 1
		FROM SYS.DATABASE_MIRRORING
		WHERE ISNULL(MIRRORING_STATE,4) NOT IN (2,4)
			AND EXISTS(SELECT 1 FROM DBO.BACKUP_DBLIST))
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''MIRRORING_STATUS'',1

		----MIRRORING_DEPLOY
                IF EXISTS(SELECT 1
                FROM master.sys.DATABASES A LEFT JOIN SYS.DATABASE_MIRRORING B
                        ON A.DATABASE_ID = B.DATABASE_ID
                WHERE A.DATABASE_ID > 4
                AND A.IS_READ_ONLY = 0
                AND A.IS_DISTRIBUTOR = 0
                AND A.STATE = 0
                AND B.MIRRORING_STATE IS NULL
                AND A.recovery_model=1
                AND A.name not in(''monitor'')
                AND A.name not in(select name from monitor.dbo.MIRRORING_FILTER))
                AND NOT EXISTS(select 1 from master.SYS.DATABASE_MIRRORING where mirroring_role=2 )
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''MIRRORING_DEPLOY'',1
		
		--SNAPSHOT_DEPLOY
		IF EXISTS(SELECT 1
		FROM SYS.DATABASE_MIRRORING A LEFT JOIN SYS.DATABASES B
			ON DB_NAME(A.DATABASE_ID)+''_DR'' = B.NAME
				AND B.IS_READ_ONLY = 1
		WHERE A.MIRRORING_STATE = 4
			AND A.MIRRORING_ROLE = 2
			AND (B.NAME IS NULL
			OR B.STATE = 4))
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''SNAPSHOT_DEPLOY'',1


		--LOGFILE_SIZE_GB
		IF EXISTS(SELECT 1
		FROM SYS.MASTER_FILES A,MONITOR.DBO.BACKUP_DBLIST B,DBO.MONITOR_FILTER_SETTING C
		WHERE C.NAME = ''LOGFILE_SIZE_GB''
			AND A.DATABASE_ID  = B.DATABASE_ID
			AND A.TYPE = 1
			AND SIZE > C.VALUE*1024*1024/8)
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''LOGFILE_SIZE_GB'',1
		
		--FULL_BACKUP_FAIL
		IF EXISTS(SELECT 1
		FROM DBO.BACKUP_TRACE A,DBO.MONITOR_FILTER_SETTING B
		WHERE A.TYPE = 1
			AND SUCCESS = 0
			AND B.NAME = ''FULL_BACKUP_FAIL''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE()))
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''FULL_BACKUP_FAIL'',1
		
		--LOG_BACKUP_FAIL
		IF EXISTS(SELECT 1
		FROM DBO.BACKUP_TRACE A,DBO.MONITOR_FILTER_SETTING B
		WHERE A.TYPE = 2
			AND SUCCESS = 0
			AND B.NAME = ''LOG_BACKUP_FAIL''
			AND A.WRITETIME > DATEADD(MI,-1,GETDATE()))
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''LOG_BACKUP_FAIL'',1

		--LOGMAN_STATUS
		IF NOT EXISTS(SELECT 1
		FROM DBO.PERFORMANCESLOG
		WHERE CATEGORYNAME = ''Processor''
			AND COUNTERNAME = ''% Processor Time''
			AND INSTANCENAME = ''_Total''
				AND WRITETIME > DATEADD(MI,-1,GETDATE()))
		AND @@SERVICENAME IN(''MSSQLSERVER'',''S1'')
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''LOGMAN_STATUS'',1

		--JOB_FAIL
		IF EXISTS(SELECT 1
		FROM MSDB.DBO.SYSJOBHISTORY A,MSDB.DBO.SYSJOBS B
		WHERE A.JOB_ID = B.JOB_ID
			AND A.RUN_DATE = CONVERT(CHAR(8),GETDATE(),112)
			AND RIGHT(''000000''+LTRIM(A.RUN_TIME),6) >= LEFT(REPLACE(CONVERT(CHAR(30),DATEADD(MI,-5,GETDATE()),114),'':'',''''),LEN(REPLACE(CONVERT(CHAR(30),DATEADD(MI,-5,GETDATE()),114),'':'',''''))-3)
			AND A.RUN_STATUS = 0) AND NOT EXISTS(select 1 from master.sys.database_mirroring where mirroring_guid is not null and mirroring_role=2)
		INSERT INTO OPENROWSET(''SQLNCLI'','''+IP+','+PORT+''';'''+ACCOUNT+''';'''+PWD+''','+DBNAME+'.DBO.PRIMITIVELOG)(APPCODE,IP,PORT,TYPE,VALUE)
		SELECT '''+@APPCODE+''','''+@IP+''','+@PORT+',''JOB_FAIL'',1'
		FROM DBO.MONITOR_SERVER_SETTING
		WHERE [STATE] = 1
		--PRINT(@SQL)
		EXEC(@SQL)
		
END
GO

USE [Monitor]
GO

IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_UPDATESTATS]') AND type in (N'P'))
DROP PROCEDURE [dbo].[JOB_UPDATESTATS]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


CREATE PROCEDURE [dbo].[JOB_UPDATESTATS]
AS
BEGIN

	SET NOCOUNT ON
	DECLARE @SQL VARCHAR(MAX)
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

USE [Monitor]
GO
IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[JOB_SNAPSHOT_DAY]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[JOB_SNAPSHOT_DAY]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [dbo].[JOB_SNAPSHOT_DAY]
AS
BEGIN

	SET NOCOUNT ON
	DECLARE @PORT VARCHAR(10)
	EXEC MONITOR.DBO.TOOL_GET_IPPORT NULL,@PORT OUTPUT
	
	DECLARE @D1 varchar(10),@D2 varchar(10)
	SET @D1=CONVERT(varchar(10),getdate(),112)
	SET @D2=CONVERT(varchar(10),getdate()-3,112)
	
	--删除dr库
	DECLARE @DELETEDR VARCHAR(MAX)
	SELECT @DELETEDR =ISNULL(@DELETEDR+'','')+'DROP DATABASE '+NAME+';'
	FROM SYS.DATABASES 
	WHERE (name like '%_'+@D2 or name like '%_'+@D1)
	AND snapshot_isolation_state=1
	--PRINT(@DELETEDR)
	EXEC(@DELETEDR)
	
	IF OBJECT_ID('TEMPDB.DBO.#SNAPSHOTDB','U') IS NOT NULL
		DROP TABLE #SNAPSHOTDB
	
	SELECT A.NAME AS MIRROR_DBNAME,A.NAME+'_'+@D1 AS SNAPSHOT_DBNAME 
	INTO #SNAPSHOTDB
	FROM SYS.DATABASES A,SYS.DATABASE_MIRRORING B
	WHERE A.DATABASE_ID > 4
		AND A.DATABASE_ID = B.DATABASE_ID
		AND A.STATE = 1
		AND A.IS_READ_ONLY = 0
		AND B.MIRRORING_STATE IS NOT NULL
		AND A.snapshot_isolation_state=0

	--删除遗留的快照文件
	DECLARE @DELETEDRFILES VARCHAR(MAX)
	SELECT @DELETEDRFILES = ISNULL(@DELETEDRFILES+'','')+'EXEC MASTER.DBO.xp_cmdshell ''del /q d:\gamedb\'+SNAPSHOT_DBNAME+'.'+@PORT+'.*.spst'';'
	FROM #SNAPSHOTDB
	--PRINT(@DELETEDRFILES)
	EXEC(@DELETEDRFILES)

	--生成快照(镜像状态正常)
	DECLARE @SQL VARCHAR(MAX)
	
	SELECT @SQL =ISNULL(@SQL+'','')+'
	DECLARE @SQL_'+UPPER(A.NAME)+' VARCHAR(MAX)
	SELECT @SQL_'+UPPER(A.NAME)+' = ISNULL(@SQL_'+UPPER(A.NAME)+'+'','','''')+''(NAME=''''''+B.NAME+'''''',FILENAME = ''''D:\GAMEDB\'+C.SNAPSHOT_DBNAME+'.'+LTRIM(@PORT)+'.''+LTRIM(B.FILE_ID)+''.spst'''')''
	FROM SYS.DATABASES A,SYS.MASTER_FILES B
	WHERE A.DATABASE_ID = B.DATABASE_ID
		AND A.NAME = '''+A.NAME+'''
		AND B.TYPE = 0
	SET @SQL_'+UPPER(A.NAME)+' = ''CREATE DATABASE '+C.SNAPSHOT_DBNAME+' ON ''+@SQL_'+UPPER(A.NAME)+'+'' AS SNAPSHOT OF '+A.NAME+''';
	EXEC(@SQL_'+UPPER(A.NAME)+');'
	FROM SYS.DATABASES A,SYS.DATABASE_MIRRORING B,#SNAPSHOTDB C
	WHERE A.DATABASE_ID > 4
		AND A.DATABASE_ID = B.DATABASE_ID
		AND A.NAME = C.MIRROR_DBNAME
		AND A.STATE = 1
		AND A.IS_READ_ONLY = 0
		AND B.MIRRORING_STATE IN (4,6)
	--PRINT(@SQL)
	EXEC(@SQL)
END
GO
--***************************************** INIT DATA ***********************************
DECLARE @PORT VARCHAR(100)
EXEC DBO.TOOL_GET_IPPORT NULL,@PORT OUTPUT

IF NOT EXISTS(SELECT 1 FROM DBO.BACKUP_SETTING)
	INSERT INTO DBO.BACKUP_SETTING(APP,FULL_BACKUP_PATH,LOG_BACKUP_PATH,KEEP_FULL_BACKUP_DAYS,KEEP_LOG_BACKUP_DAYS,FULL_BACKUP_MIN_SIZE_MB,LOG_BACKUP_MIN_SIZE_MB,UPLOAD,MD5) VALUES('sqlserver','D:\dbbak\full\','D:\dbbak\log\',2,2,40960,30720,1,1)

TRUNCATE TABLE DBO.MONITOR_COUNTERPATH
INSERT INTO DBO.MONITOR_COUNTERPATH(TYPE,COUNTERPATH)
SELECT 0,'"\Processor(_Total)\% Processor Time"' UNION ALL
SELECT 0,'"\Memory\Available MBytes"' UNION ALL
SELECT 0,'"\LogicalDisk(C:)\Free Megabytes"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\Free Megabytes"' UNION ALL
SELECT 0,'"\LogicalDisk(E:)\Free Megabytes"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\% Idle Time"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\% Disk Time"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\Avg. Disk sec/Read"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\Avg. Disk sec/Write"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\Avg. Disk Bytes/Read"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\Avg. Disk Bytes/Write"' UNION ALL
SELECT 0,'"\LogicalDisk(D:)\Avg. Disk Queue Length"' UNION ALL

--COUNTER最长两级,第三级移动至第一级,并加入(),譬如"\LogicalDisk\% Idle Time\1 D:"应该更改为"\LogicalDisk(1 D:)\% Idle Time"
SELECT 1,'"\:DataBases(_Total)\Data File(s) Size (KB)"' UNION ALL
SELECT 1,'"\:DataBases(_Total)\Log File(s) Size (KB)"' UNION ALL
SELECT 1,'"\:Databases(_Total)\Transactions/sec"' UNION ALL			--TPS
SELECT 1,'"\:General Statistics\User Connections"' UNION ALL
SELECT 1,'"\:Access Methods\Full Scans/sec"' UNION ALL				--全表扫描每秒
SELECT 1,'"\:Buffer Manager\Buffer cache hit ratio"' UNION ALL		--缓存命中率
SELECT 1,'"\:Memory Manager\Total Server Memory (KB)"' UNION ALL
SELECT 1,'"\:Latches\Latch Waits/sec"' UNION ALL
SELECT 1,'"\:Locks(_Total)\Lock Requests/sec"' UNION ALL
SELECT 1,'"\:Plan Cache(_Total)\Cache Hit Ratio"' UNION ALL
SELECT 1,'"\:SQL Errors(User Errors)\Errors/sec"' UNION ALL
SELECT 1,'"\:SQL Statistics\Batch Requests/sec"' UNION ALL			--QPS
SELECT 1,'"\:SQL Statistics\SQL Compilations/sec"' UNION ALL
SELECT 1,'"\:SQL Statistics\SQL Re-Compilations/sec"' UNION ALL
SELECT 1,'"\:Wait Statistics(Average wait time (ms))\Lock waits"' UNION ALL
SELECT 1,'"\:Wait Statistics(Average wait time (ms))\Network IO waits"' UNION ALL
SELECT 1,'"\:Wait Statistics(Average wait time (ms))\Page IO latch waits"' UNION ALL
SELECT 1,'"\:Workload Group Stats(default)\Requests completed/sec"'

TRUNCATE TABLE DBO.BACKUP_FILTER
INSERT INTO DBO.BACKUP_FILTER(NAME) VALUES('Monitor')

TRUNCATE TABLE DBO.TRACE_SETTING
INSERT INTO DBO.TRACE_SETTING(NAME,VALUE)
SELECT 'FILTER_DURATION',1 UNION ALL	--筛选执行时间大于等于?秒
SELECT 'KEEP_DATA_DAYS',60				--跟踪的数据保留多少天(数据量可能会比较大,虐心SQL)



TRUNCATE TABLE DBO.COUNTER_SETTING
INSERT INTO DBO.COUNTER_SETTING(NAME,VALUE)
SELECT 'KEEP_DATA_DAYS',60				--性能数据保留多少天

--性能数据筛选器
TRUNCATE TABLE DBO.MONITOR_FILTER_SETTING
INSERT INTO DBO.MONITOR_FILTER_SETTING(NAME,VALUE)
SELECT 'DISK_C_FREE_MB',	10240 UNION ALL
SELECT 'DISK_D_FREE_MB',	40960 UNION ALL
SELECT 'DISK_E_FREE_MB',	10240 UNION ALL
SELECT 'CPU_USE_PERCENT',	60 UNION ALL
SELECT 'IO_IDLE_PERCENT',	50 UNION ALL
SELECT 'MEMORY_FREE_MB',	512 UNION ALL
SELECT 'MIRRORING_LOG_SEND_QUEUE_KB',1048576 UNION ALL
SELECT 'LOGFILE_SIZE_GB',	40 UNION ALL
SELECT 'USER_CONNECTION_NUMBER',10000 UNION ALL
SELECT 'SLOW_QUERY_IN_5MI',5 UNION ALL
SELECT 'FULL_BACKUP_FAIL',1 UNION ALL
SELECT 'LOG_BACKUP_FAIL',1 UNION ALL
SELECT 'LOGMAN_STATUS',1

TRUNCATE TABLE DBO.MONITOR_SERVICE
INSERT INTO DBO.MONITOR_SERVICE(NAME,MONITOR_SERVICE_NAME,PORT)
SELECT @@SERVICENAME,CASE WHEN @@SERVICENAME = 'MSSQLSERVER' THEN 'SQLSERVER' ELSE 'MSSQL$'+@@SERVICENAME END,@PORT
GO

delete from MONITOR.DBO.APP_SETTING
insert into MONITOR.DBO.APP_SETTING values('blackdesert')
insert into MONITOR.DBO.APP_SETTING values('hssmpc')
GO
--****************************************** JOB ****************************************
DECLARE @SQL VARCHAR(8000)
SELECT @SQL = ISNULL(@SQL+'
','')+'EXEC MSDB.DBO.SP_DELETE_JOB @JOB_NAME='''+NAME+''',@DELETE_UNUSED_SCHEDULE=1'
FROM MSDB.DBO.SYSJOBS
WHERE NAME IN('[dbo]-backup-day','[dbo]-backup-time','snapshot','Sys_CheckPorcess','PRIVATE_QQHX_SNAPSHOT_ONE','snapshot_qqhx','PUBLIC_SNAPSHOT','slow_query_catch')
	OR NAME LIKE 'JOB_BUILDXML%'
	OR NAME LIKE 'REPLCHECK%'
	OR NAME LIKE 'TC%'
--PRINT(@SQL)
EXEC(@SQL)
GO



--如果存在镜像db,那么创建TC_SNAPSHOT
USE MASTER
GO
IF EXISTS(SELECT 1 FROM SYS.DATABASE_MIRRORING WHERE MIRRORING_STATE IS NOT NULL AND MIRRORING_ROLE = 2)
	EXEC MONITOR.DBO.TOOL_DEPLOY_SNAPSHOT 'TC_SNAPSHOT',0
GO

--如果存在复制,那么执行DBO.TOOL_DEPLOY_REPL_MONITOR
IF EXISTS(SELECT 1 FROM SYS.DATABASES WHERE STATE = 0 AND IS_DISTRIBUTOR = 0 AND IS_PUBLISHED = 1)
	EXEC MONITOR.DBO.TOOL_DEPLOY_REPL_MONITOR
GO
USE MSDB
GO

DECLARE @jobId BINARY(16)

DECLARE @JOBNAME VARCHAR(2000),@SERVERNAME VARCHAR(2000)
DECLARE @STEPNAME VARCHAR(2000),@DBNAME VARCHAR(2000)
DECLARE @SCHEDULENAME VARCHAR(2000),@CMD VARCHAR(2000)

SELECT @JOBNAME='TC_REPORT_LOAD',
	@STEPNAME='step_1',@DBNAME='master',
	@SCHEDULENAME='schedule_1',@CMD='EXEC MONITOR.DBO.JOB_REPORT_LOAD',
	@SERVERNAME=CAST(SERVERPROPERTY('SERVERNAME') AS SYSNAME)

IF EXISTS(SELECT 1 FROM dbo.sysjobs WHERE NAME=@JOBNAME)
BEGIN
	EXEC msdb.dbo.sp_delete_job @job_name=@JOBNAME,@delete_unused_schedule=1
END
EXEC  msdb.dbo.sp_add_job @job_name=@JOBNAME,
		@enabled=1,
		@notify_level_eventlog=0,
		@notify_level_email=2,
		@notify_level_netsend=2,
		@notify_level_page=2,
		@delete_level=0,
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name='sa',@job_id = @jobId OUTPUT


EXEC msdb.dbo.sp_add_jobserver @job_name=@JOBNAME,@server_name = @SERVERNAME

USE [msdb]

EXEC msdb.dbo.sp_add_jobstep @job_name=@JOBNAME,@step_name=@STEPNAME,
		@step_id=1,
		@cmdexec_success_code=0,
		@on_success_action=1,
		@on_fail_action=2,
		@retry_attempts=0,
		@retry_interval=0,
		@os_run_priority=0,@subsystem=N'TSQL',
		@command=@CMD,
		@database_name=@DBNAME,
		@flags=0

USE [msdb]

EXEC msdb.dbo.sp_update_job @job_name=@JOBNAME,
		@enabled=1,
		@start_step_id=1,
		@notify_level_eventlog=0,
		@notify_level_email=2,
		@notify_level_netsend=2,
		@notify_level_page=2,
		@delete_level=0,
		@description=N'',
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name='sa',
		@notify_email_operator_name=N'',
		@notify_netsend_operator_name=N'',
		@notify_page_operator_name=N''

USE [msdb]

DECLARE @schedule_id int
EXEC msdb.dbo.sp_add_jobschedule @job_name=@JOBNAME,@name=@SCHEDULENAME,
		@enabled=1,
		@freq_type=4,
		@freq_interval=1,
		@freq_subday_type=4,
		@freq_subday_interval=1,--5分钟一次
		@freq_relative_interval=0,
		@freq_recurrence_factor=1,
		@active_start_date=20130723,
		@active_end_date=99991231,
		@active_start_time=0,
		@active_end_time=235959,@schedule_id = @schedule_id OUTPUT
SELECT @jobId AS JOBID,@schedule_id AS SCHEDULE_ID

GO

DECLARE @jobId BINARY(16)

DECLARE @JOBNAME VARCHAR(2000),@SERVERNAME VARCHAR(2000)
DECLARE @STEPNAME VARCHAR(2000),@DBNAME VARCHAR(2000)
DECLARE @SCHEDULENAME VARCHAR(2000),@CMD VARCHAR(2000)

SELECT @JOBNAME='TC_TRACE',
	@STEPNAME='step_1',@DBNAME='MASTER',
	@SCHEDULENAME='schedule_1',@CMD='EXEC MONITOR.DBO.JOB_TRACE 1',
	@SERVERNAME=CAST(SERVERPROPERTY('SERVERNAME') AS SYSNAME)

IF EXISTS(SELECT 1 FROM MSDB.DBO.SYSJOBS WHERE NAME=@JOBNAME)
BEGIN
	EXEC msdb.dbo.sp_delete_job @job_name=@JOBNAME,@delete_unused_schedule=1
END
EXEC  msdb.dbo.sp_add_job @job_name=@JOBNAME,
		@enabled=1,
		@notify_level_eventlog=0,
		@notify_level_email=2,
		@notify_level_netsend=2,
		@notify_level_page=2,
		@delete_level=0,
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name='sa',@job_id = @jobId OUTPUT

EXEC msdb.dbo.sp_add_jobserver @job_name=@JOBNAME,@server_name = @SERVERNAME

USE [msdb]

EXEC msdb.dbo.sp_add_jobstep @job_name=@JOBNAME,@step_name=@STEPNAME,
		@step_id=1,
		@cmdexec_success_code=0,
		@on_success_action=1,
		@on_fail_action=2,
		@retry_attempts=0,
		@retry_interval=0,
		@os_run_priority=0,@subsystem=N'TSQL',
		@command=@CMD,
		@database_name=@DBNAME,
		@flags=0

USE [msdb]

EXEC msdb.dbo.sp_update_job @job_name=@JOBNAME,
		@enabled=1,
		@start_step_id=1,
		@notify_level_eventlog=0,
		@notify_level_email=2,
		@notify_level_netsend=2,
		@notify_level_page=2,
		@delete_level=0,
		@description=N'',
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name='sa',
		@notify_email_operator_name=N'',
		@notify_netsend_operator_name=N'',
		@notify_page_operator_name=N''

USE [msdb]

DECLARE @schedule_id int
EXEC msdb.dbo.sp_add_jobschedule @job_name=@JOBNAME,@name=@SCHEDULENAME,
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
		@active_end_time=235959,@schedule_id = @schedule_id OUTPUT
SELECT @jobId AS JOBID,@schedule_id AS SCHEDULE_ID

GO

DECLARE @jobId BINARY(16)
IF EXISTS(SELECT 1 FROM MSDB.DBO.SYSJOBS WHERE NAME=N'TC_BACKUP_FULL')
BEGIN
	EXEC msdb.dbo.sp_delete_job @job_name=N'TC_BACKUP_FULL',@delete_unused_schedule=1
END
EXEC msdb.dbo.sp_add_job @job_name=N'TC_BACKUP_FULL',
		@enabled=1,
		@notify_level_eventlog=0,
		@notify_level_email=0,
		@notify_level_netsend=0,
		@notify_level_page=0,
		@delete_level=0,
		@description=N'No description available.',
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name=N'sa',@job_id = @jobId OUTPUT

DECLARE @ON_SUCCESS_ACTION INT = 1,@ON_FAIL_ACTION INT = 2

EXEC msdb.dbo.sp_add_jobstep @job_id=@jobId,@step_name=N'TC_BACKUP_FULL_1',
		@step_id=1,
		@cmdexec_success_code=0,
		@on_success_action=@ON_SUCCESS_ACTION,
		@on_success_step_id=0,
		@on_fail_action=@ON_FAIL_ACTION,
		@on_fail_step_id=0,
		@retry_attempts=0,
		@retry_interval=0,
		@os_run_priority=0,@subsystem=N'TSQL',
		@command=N'EXEC MONITOR.DBO.TOOL_BACKUP_DATABASE 1',
		@database_name=N'master',
		@flags=0

EXEC msdb.dbo.sp_update_job @job_id = @jobId,@start_step_id = 1

EXEC  msdb.dbo.sp_add_jobschedule @job_id=@jobId,@name=N'TC_BACKUP_FULL_1',
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
EXEC msdb.dbo.sp_add_jobserver @job_id = @jobId,@server_name = N'(local)'
SELECT @jobId AS JOBID
GO


DECLARE @jobId BINARY(16)
IF EXISTS(SELECT 1 FROM MSDB.DBO.SYSJOBS WHERE NAME=N'TC_BACKUP_LOG')
BEGIN
	EXEC msdb.dbo.sp_delete_job @job_name=N'TC_BACKUP_LOG',@delete_unused_schedule=1
END
EXEC msdb.dbo.sp_add_job @job_name=N'TC_BACKUP_LOG',
		@enabled=1,
		@notify_level_eventlog=0,
		@notify_level_email=0,
		@notify_level_netsend=0,
		@notify_level_page=0,
		@delete_level=0,
		@description=N'No description available.',
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name=N'sa',@job_id = @jobId OUTPUT

EXEC msdb.dbo.sp_add_jobstep @job_id=@jobId,@step_name=N'TC_BACKUP_LOG_1',
		@step_id=1,
		@cmdexec_success_code=0,
		@on_success_action=1,
		@on_success_step_id=0,
		@on_fail_action=2,
		@on_fail_step_id=0,
		@retry_attempts=0,
		@retry_interval=0,
		@os_run_priority=0,@subsystem=N'TSQL',
		@command=N'EXEC MONITOR.DBO.TOOL_BACKUP_DATABASE 2',
		@database_name=N'master',
		@flags=0

EXEC msdb.dbo.sp_update_job @job_id = @jobId,@start_step_id = 1

EXEC msdb.dbo.sp_add_jobschedule @job_id=@jobId,@name=N'TC_BACKUP_LOG_1',
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
EXEC msdb.dbo.sp_add_jobserver @job_id = @jobId,@server_name = N'(local)'
SELECT @jobId AS JOBID
GO


DECLARE @jobId BINARY(16)
IF EXISTS(SELECT 1 FROM MSDB.DBO.SYSJOBS WHERE NAME=N'TC_MONITOR_FILTER')
BEGIN
	EXEC msdb.dbo.sp_delete_job @job_name=N'TC_MONITOR_FILTER',@delete_unused_schedule=1
END
EXEC msdb.dbo.sp_add_job @job_name=N'TC_MONITOR_FILTER',
		@enabled=1,
		@notify_level_eventlog=0,
		@notify_level_email=0,
		@notify_level_netsend=0,
		@notify_level_page=0,
		@delete_level=0,
		@description=N'No description available.',
		@category_name=N'[Uncategorized (Local)]',
		@owner_login_name=N'sa',@job_id = @jobId OUTPUT

EXEC msdb.dbo.sp_add_jobstep @job_id=@jobId,@step_name=N'TC_MONITOR_FILTER_1',
		@step_id=1,
		@cmdexec_success_code=0,
		@on_success_action=1,
		@on_success_step_id=0,
		@on_fail_action=2,
		@on_fail_step_id=0,
		@retry_attempts=0,
		@retry_interval=0,
		@os_run_priority=0,@subsystem=N'TSQL',
		@command=N'EXEC DBO.JOB_MONITOR_FILTER',
		@database_name=N'MONITOR',
		@flags=0

EXEC msdb.dbo.sp_update_job @job_id = @jobId,@start_step_id = 1

EXEC msdb.dbo.sp_add_jobschedule @job_id=@jobId,@name=N'TC_MONITOR_FILTER_1',
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

EXEC  msdb.dbo.sp_add_jobserver @job_id = @jobId,@server_name = N'(local)'
SELECT @jobId AS JOBID
GO

USE [msdb]
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs_view WHERE name = N'TC_SNAPSHOT_DAY')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_SNAPSHOT_DAY', @delete_unused_schedule=1
GO

USE [msdb]
GO

/****** Object:  Job [TC_SNAPSHOT_DAY]    Script Date: 11/02/2021 15:21:45 ******/
BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]]    Script Date: 11/02/2021 15:21:45 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_SNAPSHOT_DAY', 
		@enabled=0, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_SNAPSHOT_1]    Script Date: 11/02/2021 15:21:45 ******/
EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'TC_SNAPSHOT_1', 
		@step_id=1, 
		@cmdexec_success_code=0, 
		@on_success_action=1, 
		@on_success_step_id=0, 
		@on_fail_action=2, 
		@on_fail_step_id=0, 
		@retry_attempts=0, 
		@retry_interval=0, 
		@os_run_priority=0, @subsystem=N'TSQL', 
		@command=N'EXEC MONITOR.DBO.JOB_SNAPSHOT_DAY', 
		@database_name=N'MASTER', 
		@flags=0
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = 1
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'TC_SNAPSHOT_DAY', 
		@enabled=1, 
		@freq_type=4, 
		@freq_interval=1, 
		@freq_subday_type=1, 
		@freq_subday_interval=0, 
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


USE [msdb]
GO

IF  EXISTS (SELECT job_id FROM msdb.dbo.sysjobs_view WHERE name = N'TC_UPDATESTATS')
EXEC msdb.dbo.sp_delete_job @job_name=N'TC_UPDATESTATS', @delete_unused_schedule=1
GO

BEGIN TRANSACTION
DECLARE @ReturnCode INT
SELECT @ReturnCode = 0
/****** Object:  JobCategory [[Uncategorized (Local)]]    Script Date: 2021/11/9 23:25:07 ******/
IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'[Uncategorized (Local)]' AND category_class=1)
BEGIN
EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'JOB', @type=N'LOCAL', @name=N'[Uncategorized (Local)]'
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback

END

DECLARE @jobId BINARY(16)
EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'TC_UPDATESTATS', 
		@enabled=0, 
		@notify_level_eventlog=0, 
		@notify_level_email=0, 
		@notify_level_netsend=0, 
		@notify_level_page=0, 
		@delete_level=0, 
		@description=N'No description available.', 
		@category_name=N'[Uncategorized (Local)]', 
		@owner_login_name=N'sa', @job_id = @jobId OUTPUT
IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback
/****** Object:  Step [TC_UPDATESTATS_1]    Script Date: 2021/11/9 23:25:07 ******/
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
		@active_end_time=235959
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
