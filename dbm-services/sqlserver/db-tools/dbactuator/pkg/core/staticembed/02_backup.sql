USE Monitor
SET QUOTED_IDENTIFIER ON
SET NOCOUNT ON
GO
IF OBJECT_ID('DBO.TOOL_BACKUP_DATABASE','P') IS NOT NULL
	DROP PROC DBO.TOOL_BACKUP_DATABASE
GO
IF OBJECT_ID('DBO.TOOL_BACKUP_DATABASE_OPERATOR','P') IS NOT NULL
	DROP PROC DBO.TOOL_BACKUP_DATABASE_OPERATOR
GO
IF OBJECT_ID('DBO.TOOL_CHECK_DISK_FREE_SIZE','P') IS NOT NULL
	DROP PROC DBO.TOOL_CHECK_DISK_FREE_SIZE
GO
IF OBJECT_ID('DBO.sp_dbo_do_log_backup','P') IS NOT NULL
	DROP PROC DBO.sp_dbo_do_log_backup
GO
IF OBJECT_ID('DBO.sp_dbo_do_diff_backup','P') IS NOT NULL
	DROP PROC DBO.sp_dbo_do_diff_backup
GO
IF OBJECT_ID('DBO.sp_dbo_dbbackup','P') IS NOT NULL
	DROP PROC DBO.sp_dbo_dbbackup
GO

IF OBJECT_ID('DBO.TOOL_BACKUP_XML','P') IS NOT NULL
	DROP PROC DBO.TOOL_BACKUP_XML
GO

IF OBJECT_ID('DBO.TOOL_BACKUP_XML_LOG_DAILY','P') IS NOT NULL
	DROP PROC DBO.TOOL_BACKUP_XML_LOG_DAILY
GO

CREATE PROCEDURE DBO.TOOL_BACKUP_XML
@FILENAME VARCHAR(1000),
@IP VARCHAR(100),
@PORT VARCHAR(100)
AS
BEGIN
	DECLARE @CMD VARCHAR(8000),
			@XML VARCHAR(8000),
			
			@APP VARCHAR(100),
			@TYPE INT,
			@DBNAME VARCHAR(1000),
			@PATH VARCHAR(1000),
			@STARTTIME VARCHAR(100),
			@ENDTIME VARCHAR(100),
			
			@FILESIZE BIGINT = 0,
			@MD5CODE VARCHAR(100) = 'nocheck',
			@INSTANCE_DBNAME_LIST VARCHAR(8000)
			
	SELECT @TYPE = TYPE,@DBNAME = DBNAME,@PATH = PATH,@STARTTIME = CONVERT(CHAR(19),STARTTIME,120),@ENDTIME = CONVERT(CHAR(19),ENDTIME,120)
	FROM MONITOR.DBO.BACKUP_TRACE
	WHERE FILENAME = @FILENAME
	
	SELECT @APP = APP FROM MONITOR.DBO.BACKUP_SETTING
	SELECT @INSTANCE_DBNAME_LIST = ISNULL(@INSTANCE_DBNAME_LIST+',','')+NAME FROM MONITOR.DBO.BACKUP_DBLIST
	
	--get filesize
	SET @CMD = LEFT(@PATH,2)+' && CD '+@PATH+' && FOR /F %I IN (''DIR /B '+@PATH+@FILENAME+''') DO ECHO %~ZI'
	TRUNCATE TABLE DBO.BACKUP_COMMON_TABLE
	INSERT INTO DBO.BACKUP_COMMON_TABLE EXEC XP_CMDSHELL @CMD
	DELETE DBO.BACKUP_COMMON_TABLE
	WHERE BLOCK IS NULL
		OR BLOCK LIKE '%ECHO%'
		OR BLOCK LIKE '%recognized as an internal%'
		OR BLOCK LIKE '%or batch file%'
		OR BLOCK LIKE '%File Not Found%'
		OR BLOCK LIKE '%The system cannot find%'

	IF EXISTS(SELECT 1 FROM DBO.BACKUP_COMMON_TABLE)
		SELECT @FILESIZE = BLOCK FROM DBO.BACKUP_COMMON_TABLE
	
	--get md5
	SET @CMD = 'CERTUTIL -HASHFILE '+@PATH+@FILENAME+' MD5'
	TRUNCATE TABLE DBO.BACKUP_COMMON_TABLE
	INSERT INTO DBO.BACKUP_COMMON_TABLE EXEC XP_CMDSHELL @CMD
	DELETE DBO.BACKUP_COMMON_TABLE WHERE BLOCK LIKE 'MD5 HASH%' OR BLOCK LIKE 'CERTUTIL:%' OR BLOCK IS NULL
	IF EXISTS(SELECT 1 FROM .DBO.BACKUP_COMMON_TABLE)
		SELECT @MD5CODE = REPLACE(BLOCK,' ','') FROM DBO.BACKUP_COMMON_TABLE
	
	--build pub file
	SET @CMD = 'echo NAME='+@PATH+@FILENAME+'> D:\IEOD_FILE_BACKUP\'+@FILENAME+'.PUB'
	EXEC XP_CMDSHELL @CMD
	SET @CMD = 'echo MD5='+@MD5CODE+'>>'+'D:\IEOD_FILE_BACKUP\'+@FILENAME+'.PUB'
	EXEC XP_CMDSHELL @CMD
	SET @CMD = 'echo BINDIP='+@IP+'>>'+'D:\IEOD_FILE_BACKUP\'+@FILENAME+'.PUB'
	EXEC XP_CMDSHELL @CMD
	SET @CMD = 'echo TAG='+CASE WHEN @TYPE = 1 THEN 'MSSQL_FULL_BACKUP' ELSE 'INCREMENT_BACKUP' END+'>>'+'D:\IEOD_FILE_BACKUP\'+@FILENAME+'.PUB'
	EXEC XP_CMDSHELL @CMD
	SET @CMD = 'echo BUNAME=dbo>>'+'D:\IEOD_FILE_BACKUP\'+@FILENAME+'.PUB'
	EXEC XP_CMDSHELL @CMD
	
	--update history
	UPDATE DBO.BACKUP_TRACE SET FILESIZE = @FILESIZE,MD5CODE = @MD5CODE,UPLOADED = 1 WHERE FILENAME = @FILENAME

	--build xml file
	DECLARE @DATETIME VARCHAR(23) = CONVERT(VARCHAR(19),GETDATE(),120)
	SET @XML = NULL
	IF @TYPE = 1
	BEGIN
		SET @XML = 'D:\dbbak\backup_report_'+@@SERVICENAME+'.'+@DBNAME+'.xml'
		
		SET @CMD = 'echo ^<?xml version=''1.0'' encoding="iso-8859-1" ?^> >'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_data name="rotate_report"^> >>'+@XML EXEC XP_CMDSHELL @CMD
		
		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_port^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>'+@PORT+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		
		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_Btime1^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>'+@STARTTIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD

		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_Btime2^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>'+@ENDTIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD

		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_BtypeID^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>256^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		
		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_Bfname^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>'+@FILENAME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD

		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_Bfsize^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>'+LTRIM(@FILESIZE)+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD

		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="report_time"^>'+@DATETIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="name"^>dbbackup_dblist^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo	^<xml_field name="value"^>'+@DBNAME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD

		SET @CMD = 'echo ^</xml_data^> >>'+@XML EXEC XP_CMDSHELL @CMD
		
		--send xml
		IF LEN(@XML) > 0
		BEGIN
			--SET @CMD = 'cd d:\dbbak && d: && d:\perl\bin\perl.exe send_xml.pl -c '+@XML+' -t 60'
			SET @CMD='cd d:\dbbak && d: && C:\cygwinroot\bin\sh.exe send_xml.sh general_log '+@XML+''
			EXEC XP_CMDSHELL @CMD
		END
		
		--NEW XML
		SET @XML = 'D:\dbbak\backup_report_'+@@SERVICENAME+'_NEWXML.'+@DBNAME+'.xml'
		
		SET @CMD = 'echo ^<?xml version=''1.0'' encoding="iso-8859-1" ?^> >'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo ^<xml_data name="dbbackup_info_other"^> >>'+@XML EXEC XP_CMDSHELL @CMD
		
		SET @CMD = 'echo  ^<xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="port"^>'+@PORT+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="real_port"^>'+@PORT+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="real_host"^>'+@IP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="end_time"^>'+@ENDTIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="begin_time"^>'+@STARTTIME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="file_size"^>'+LTRIM(@FILESIZE)+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="backup_dir"^>'+REPLACE(@PATH,'\','\\')+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="backup_dblist"^>'+@INSTANCE_DBNAME_LIST+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		--SET @CMD = 'echo  	^<xml_field name="backup_charset"^>NONE^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="app"^>'+@APP+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		--SET @CMD = 'echo  	^<xml_field name="backup_type"^>NONE^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="db_engine"^>S^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  	^<xml_field name="file_list"^>'+@FILENAME+'^</xml_field^> >>'+@XML EXEC XP_CMDSHELL @CMD
		SET @CMD = 'echo  ^</xml_row^> >>'+@XML EXEC XP_CMDSHELL @CMD

		SET @CMD = 'echo ^</xml_data^> >>'+@XML EXEC XP_CMDSHELL @CMD
		
		--send xml
		IF LEN(@XML) > 0
		BEGIN
			--SET @CMD = 'cd d:\dbbak && d: && d:\perl\bin\perl.exe send_xml.pl -c '+@XML+' -t 60'
			SET @CMD='cd d:\dbbak && d: && C:\cygwinroot\bin\sh.exe send_xml.sh dbbackup_info_other '+@XML+''
			EXEC XP_CMDSHELL @CMD
		END
	END
	
END

GO

CREATE PROCEDURE DBO.TOOL_BACKUP_XML_LOG_DAILY
@IP VARCHAR(100),
@PORT VARCHAR(100)
AS
BEGIN

	SET NOCOUNT ON
	DECLARE @CMD VARCHAR(8000),
			@XML VARCHAR(8000),
			@SQL_FIRST VARCHAR(MAX),
			@SQL_LAST VARCHAR(MAX)
			
	DECLARE @DATETIME VARCHAR(23) = GETDATE()

    SET @XML = NULL

	SET @XML = 'D:\dbbak\backup_report_'+@@SERVICENAME+'_daylog.xml'
	
	SET @CMD = 'echo ^<?xml version=''1.0'' encoding="iso-8859-1" ?^> >'+@XML EXEC XP_CMDSHELL @CMD
	SET @CMD = 'echo ^<xml_data name="rotate_report"^> >>'+@XML EXEC XP_CMDSHELL @CMD
	
	SET @SQL_FIRST = NULL
	--设置addmi的原因:入库表PRIMARY KEY (`report_time`,`ip`,`port`,`name`) 限制,如果不加那么会出现重复键而入库失败.
	;WITH T_FIRST AS
	(
		SELECT ROW_NUMBER()OVER(PARTITION BY A.DBNAME ORDER BY A.WRITETIME) AS INDEXNO,DB_ID(DBNAME) AS ADDMI,*
		FROM MONITOR.DBO.BACKUP_TRACE A,MONITOR.DBO.BACKUP_DBLIST B
		WHERE TYPE > 1
			AND STARTTIME >= CONVERT(CHAR(19),GETDATE(),112)
			AND A.DBNAME = B.NAME
	)
	SELECT @SQL_FIRST = ISNULL(@SQL_FIRST+CHAR(13),'')+'
	SET @CMD = ''echo  ^<xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="port"^>'+@PORT+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="report_time"^>'+CONVERT(VARCHAR(19),DATEADD(MI,ADDMI,@DATETIME),120)+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="name"^>backup_FirstBinLogName^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="value"^>'+FILENAME+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  ^</xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	
	SET @CMD = ''echo  ^<xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="port"^>'+@PORT+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="report_time"^>'+CONVERT(VARCHAR(19),DATEADD(MI,ADDMI,@DATETIME),120)+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="name"^>backup_FirstBinLogTime^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="value"^>'+FILENAME+' '+CONVERT(CHAR(19),STARTTIME,120)+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  ^</xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD'
	FROM T_FIRST WHERE INDEXNO = 1
	SET @SQL_FIRST = 'DECLARE @CMD VARCHAR(8000) '+@SQL_FIRST
	--PRINT(@SQL_FIRST)
	EXEC(@SQL_FIRST)
	
	SET @SQL_LAST = NULL
	;WITH T_LAST AS
	(
		SELECT ROW_NUMBER()OVER(PARTITION BY A.DBNAME ORDER BY A.WRITETIME DESC) AS INDEXNO,DB_ID(DBNAME) AS ADDMI,*
		FROM MONITOR.DBO.BACKUP_TRACE A,MONITOR.DBO.BACKUP_DBLIST B
		WHERE TYPE > 1
			AND STARTTIME >= CONVERT(CHAR(19),GETDATE(),112)
			AND A.DBNAME = B.NAME
	)
	SELECT @SQL_LAST = ISNULL(@SQL_LAST+CHAR(13),'')+'
	SET @CMD = ''echo  ^<xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="port"^>'+@PORT+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="report_time"^>'+CONVERT(VARCHAR(19),DATEADD(MI,ADDMI,@DATETIME),120)+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="name"^>backup_LastBinLogName^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="value"^>'+FILENAME+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  ^</xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	
	SET @CMD = ''echo  ^<xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="ip"^>'+@IP+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="port"^>'+@PORT+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  	^<xml_field name="report_time"^>'+CONVERT(VARCHAR(19),DATEADD(MI,ADDMI,@DATETIME),120)+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="name"^>backup_LastBinLogTime^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo	^<xml_field name="value"^>'++FILENAME+' '+CONVERT(CHAR(19),STARTTIME,120)+'^</xml_field^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD
	SET @CMD = ''echo  ^</xml_row^> >>'+@XML+''' EXEC XP_CMDSHELL @CMD'
	FROM T_LAST WHERE INDEXNO = 1
	SET @SQL_LAST = 'DECLARE @CMD VARCHAR(8000) '+@SQL_LAST
	--PRINT(@SQL_LAST)
	EXEC(@SQL_LAST)
	
	SET @CMD = 'echo ^</xml_data^> >>'+@XML EXEC XP_CMDSHELL @CMD
	
	--send xml
	IF LEN(@XML) > 0
	BEGIN
		--SET @CMD = 'cd d:\dbbak && d: && d:\perl\bin\perl.exe send_xml.pl -c '+@XML+' -t 60'
		SET @CMD='cd d:\dbbak && d: && C:\cygwinroot\bin\sh.exe send_xml.sh rotate_report '+@XML+''
		PRINT @CMD
		EXEC XP_CMDSHELL @CMD
	END
END

GO

CREATE PROCEDURE DBO.TOOL_BACKUP_DATABASE_OPERATOR
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

CREATE PROCEDURE DBO.TOOL_CHECK_DISK_FREE_SIZE
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


CREATE PROCEDURE DBO.TOOL_BACKUP_DATABASE
@TYPE INT = 1
AS
BEGIN
	SET NOCOUNT ON;
	DECLARE @DISK_MIN_SIZE_MB INT = 10240
	DECLARE @BACKUP_PATH VARCHAR(100) = 'D:\'
	DECLARE @KEEP_BACKUP_DAYS INT
	DECLARE @CHECKER INT = 0
	DECLARE @SUCCESS INT = 0
	DECLARE @CMD VARCHAR(8000)
	DECLARE @SUFFIX VARCHAR(10) = '.bak'
	
	DECLARE @IP VARCHAR(100),@PORT VARCHAR(100)
	DECLARE @SQL NVARCHAR(MAX),@FETCH_STATUS INT
	
	SET @SQL = NULL
	SELECT @SQL = ISNULL(@SQL+'','')+'EXEC MSDB.DBO.SP_UPDATE_JOB @JOB_NAME= N'''+A.NAME+''',@ENABLED = 0;'
	FROM MSDB.DBO.SYSJOBS A
	WHERE A.NAME IN('TC_BACKUP_LOG')
	--PRINT(@SQL)
	EXEC(@SQL)
	
	--如果有当前实例有其他备份进程,则等待3分钟
	WHILE EXISTS(SELECT 1 FROM SYS.DM_EXEC_REQUESTS WHERE COMMAND LIKE 'BACKUP%')
	BEGIN
		RAISERROR ('another backup process is running.wait 3 minute continue', 1,1)
		WAITFOR DELAY '00:03:00'
	END
	
	DECLARE	@APP VARCHAR(100),
		@FULL_BACKUP_PATH VARCHAR(100),
		@LOG_BACKUP_PATH VARCHAR(100),
		@KEEP_FULL_BACKUP_DAYS INT,
		@KEEP_LOG_BACKUP_DAYS INT,
		@FULL_BACKUP_MIN_SIZE_MB INT,
		@LOG_BACKUP_MIN_SIZE_MB INT,
		@ERROR_MESSAGE VARCHAR(4000)
	
	--获取备份配置数据
	SELECT @APP = APP,
		@FULL_BACKUP_PATH = FULL_BACKUP_PATH,
		@LOG_BACKUP_PATH = LOG_BACKUP_PATH,
		@KEEP_FULL_BACKUP_DAYS = KEEP_FULL_BACKUP_DAYS,
		@KEEP_LOG_BACKUP_DAYS = KEEP_LOG_BACKUP_DAYS,
		@FULL_BACKUP_MIN_SIZE_MB = FULL_BACKUP_MIN_SIZE_MB,
		@LOG_BACKUP_MIN_SIZE_MB = LOG_BACKUP_MIN_SIZE_MB
	FROM DBO.BACKUP_SETTING
	--获取IP,PORT
	EXEC DBO.TOOL_GET_IPPORT @IP OUTPUT,@PORT OUTPUT
	
	--定义变量
	DECLARE @CURRENT_TIME VARCHAR(20)
	DECLARE @START_TIME VARCHAR(25) = CONVERT(CHAR(19),GETDATE(),120)

	IF @TYPE = 1
		SELECT @BACKUP_PATH = @FULL_BACKUP_PATH,@KEEP_BACKUP_DAYS = @KEEP_FULL_BACKUP_DAYS,@DISK_MIN_SIZE_MB = @FULL_BACKUP_MIN_SIZE_MB,@SUFFIX = '.bak'
	ELSE
		SELECT @BACKUP_PATH = @LOG_BACKUP_PATH,@KEEP_BACKUP_DAYS = @KEEP_LOG_BACKUP_DAYS,@DISK_MIN_SIZE_MB = @LOG_BACKUP_MIN_SIZE_MB,@SUFFIX = '.trn'
	IF @TYPE = 3
		SELECT @SUFFIX = '.diff'
	
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

	BEGIN TRY
		--开始备份
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+CHAR(13),'')+'
		DECLARE @SUCCESS_'+NAME+' INT = 0,@CHECKER_'+NAME+' INT = 0
		DECLARE @STARTTIME_'+NAME+' VARCHAR(25) = CONVERT(CHAR(19),GETDATE(),120),
			@STARTTIME_SHORT_'+NAME+' VARCHAR(25) =REPLACE(REPLACE(REPLACE(CONVERT(CHAR(19),GETDATE(),120),'':'',''''),''-'',''''),'' '','''')
		DECLARE @FILENAME_'+NAME+' VARCHAR(4000) = '''+@APP+'_'+@IP+'_'+LTRIM(@PORT)+'_'+NAME+'_''+@STARTTIME_SHORT_'+NAME+'+'''+@SUFFIX+'''
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
		INSERT INTO DBO.BACKUP_TRACE(DBNAME,[PATH],FILENAME,TYPE,STARTTIME,ENDTIME,FILESIZE,MD5CODE,SUCCESS,UPLOADED,WRITETIME)
		VALUES('''+NAME+''','''+@BACKUP_PATH+''',@FILENAME_'+NAME+','+LTRIM(@TYPE)+',@STARTTIME_'+NAME+',@ENDTIME_'+NAME+',0,0,@SUCCESS_'+NAME+',0,GETDATE())'
		FROM DBO.BACKUP_DBLIST
		--PRINT(@SQL)
		EXEC (@SQL)
	END TRY
	BEGIN CATCH
		PRINT '~~ error in backup database ~~'
	END CATCH
	
	BEGIN TRY
		--开始生成文件大小和MD5码,以及上报XML
		SET @SQL = NULL
		SELECT @SQL = ISNULL(@SQL+CHAR(13),'')+'
		EXEC DBO.TOOL_BACKUP_XML '''+FILENAME+''','''+@IP+''','''+@PORT+''''
		FROM MONITOR.DBO.BACKUP_TRACE
		WHERE SUCCESS = 1 AND UPLOADED = 0 AND TYPE = @TYPE AND STARTTIME >= @START_TIME
		--PRINT(@SQL)
		EXEC (@SQL)
		
		--生成每天的日志备份上报数据
		IF (@TYPE > 1 AND DATEPART(HOUR,GETDATE()) = 23 AND DATEPART(MI,GETDATE()) >= 30 AND DATEPART(MI,GETDATE()) < 59)
		BEGIN
			EXEC MONITOR.DBO.TOOL_BACKUP_XML_LOG_DAILY @IP,@PORT
		END
		
	END TRY
	BEGIN CATCH
		PRINT '~~ error in build xml ~~'
	END CATCH
	
	SET @SQL = NULL
	SELECT @SQL = ISNULL(@SQL+'','')+'EXEC MSDB.DBO.SP_UPDATE_JOB @JOB_NAME= N'''+A.NAME+''',@ENABLED = 1;'
	FROM MSDB.DBO.SYSJOBS A
	WHERE A.NAME IN('TC_BACKUP_LOG')
	--PRINT(@SQL)
	EXEC(@SQL)
	
	--add shrink log step
	DECLARE @shrink_size bigint
	SET @shrink_size=1024
	IF EXISTS(SELECT 1 FROM [Monitor].[dbo].[BACKUP_SETTING] where APP in(SELECT APP FROM MONITOR.DBO.APP_SETTING))
		SET @shrink_size=20480
		
	SET @SQL = NULL
	SELECT @SQL = ISNULL(@SQL+';'+CHAR(13),'')+'USE ['+A.NAME+'] DBCC SHRINKFILE ('''+B.NAME+''','+convert(varchar,@shrink_size)+')'
	FROM SYS.DATABASES A,SYS.MASTER_FILES B
	WHERE A.DATABASE_ID > 4
		AND A.NAME <> 'MONITOR'
		AND A.STATE = 0
		AND A.IS_READ_ONLY = 0
		AND A.DATABASE_ID = B.DATABASE_ID
		AND B.TYPE = 1
		AND B.SIZE*8/1024/1024 >= 15
	--PRINT(@SQL)
	EXEC(@SQL)
END
GO

CREATE PROCEDURE [dbo].[sp_dbo_do_log_backup]
AS
BEGIN
	EXEC DBO.TOOL_BACKUP_DATABASE 2
END
GO
CREATE PROCEDURE [dbo].[sp_dbo_do_diff_backup]
AS
BEGIN
	EXEC DBO.TOOL_BACKUP_DATABASE 3
END
GO

CREATE PROCEDURE [dbo].[sp_dbo_dbbackup]
AS
BEGIN
	EXEC DBO.TOOL_BACKUP_DATABASE 1
END
GO
