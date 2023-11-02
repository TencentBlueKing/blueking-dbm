USE Monitor
SET QUOTED_IDENTIFIER ON
SET NOCOUNT ON
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_Suspend]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_Suspend]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_SafetyOff]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_SafetyOff]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_Resume]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_Resume]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_Remove]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_Remove]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_LossOver]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_LossOver]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_FailOver]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_FailOver]
GO
IF OBJECT_ID('DBO.[Sys_AutoSwitch_DrToDb]','P') IS NOT NULL
DROP PROC DBO.[Sys_AutoSwitch_DrToDb]
GO


/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_Suspend]    Script Date: 02/28/2015 20:29:52 ******/
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
/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_SafetyOff]    Script Date: 02/28/2015 20:29:52 ******/
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
/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_Resume]    Script Date: 02/28/2015 20:29:52 ******/
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
/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_Remove]    Script Date: 02/28/2015 20:29:52 ******/
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
/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_LossOver]    Script Date: 02/28/2015 20:29:52 ******/
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
/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_FailOver]    Script Date: 02/28/2015 20:29:52 ******/
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
/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch_DrToDb]    Script Date: 02/28/2015 20:29:52 ******/
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

/****** Object:  StoredProcedure [dbo].[Sys_AutoSwitch]    Script Date: 02/28/2015 20:29:52 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE proc [dbo].[Sys_AutoSwitch]
(@Flag tinyint)
AS

declare @r int=0;
declare @i int=1;
declare @DBname varchar(100)
declare @ERR_FAILURE INT = 1;
declare @msg varchar(1000)

BEGIN TRY
	SET @DBname='test'
	
	--检查2分钟
	while @i<=120
	begin
		--校验数据是否同步
		Exec @r=dbo.A @DBname
		if @r=1
			break
			
		waitfor time '00:00:01'
		set @i=@i+1
	end

	if @r<>1
	begin
		print 'err'
		return -1
	end

	--自动切换+断开镜像
	if @Flag=1
	begin
		--切换镜像角色
		Exec @r=Link_DB.monitor.dbo.Sys_AutoSwitch_FailOver @msg output
		if @r<>1
		begin
			print 'err2'
			return -1
		end
		
		--
		waitfor time '00:00:01'
		
		--断开镜像关系
		Exec @r=monitor.dbo.Sys_AutoSwitch_Remove @msg output
		if @r<>1
		begin
			print 'err3'
			return -1
		end

	end
	--自动切换
	else if @Flag=2
	begin
		--切换镜像角色
		Exec @r=Link_DB.monitor.dbo.Sys_AutoSwitch_FailOver @msg output
		if @r<>1
		begin
			print 'err2'
			return -1
		end
		
		Exec @r=monitor.dbo.Sys_AutoSwitch_SafetyOff @msg output
		if @r<>1
		begin
			print 'err3'
			return -1
		end
	
	end
	--强制切换
	else if @Flag=3
	begin
		--切换镜像角色
		Exec @r=monitor.dbo.Sys_AutoSwitch_LossOver @msg output
		if @r<>1
		begin
			print 'err3'
			return -1
		end
	end
	--强制切换
	else if @Flag=4
	begin
		--切换镜像角色
		Exec @r=monitor.dbo.Sys_AutoSwitch_Resume @msg output
		if @r<>1
		begin
			print 'err3'
			return -1
		end
	end
	--强制切换
	else if @Flag=5
	begin
		--切换镜像角色
		Exec @r=monitor.dbo.Sys_AutoSwitch_Remove @msg output
		if @r<>1
		begin
			print 'err3'
			return -1
		end
	end
	--强制切换
	else if @Flag=6
	begin
		--切换镜像角色
		Exec @r=monitor.dbo.Sys_AutoSwitch_SafetyOff @msg output
		if @r<>1
		begin
			print 'err3'
			return -1
		end
	end
	
	if @Flag<>0
	begin
		--检查新DB状态
		SELECT mirroring_state, mirroring_state_desc, mirroring_failover_lsn 
		FROM sys.database_mirroring 
		WHERE database_id=db_id(@DBname);
	end
	
    RETURN 1
    
END TRY
BEGIN CATCH
DECLARE	@ERR_NUMBER		INT				= ERROR_NUMBER(),
				@ERR_SEVERITY	INT				= ERROR_SEVERITY(),
				@ERR_STATE		INT				= ERROR_STATE(),
				@ERR_PROCEDURE	NVARCHAR(126)	= ERROR_PROCEDURE(),
				@ERR_MESSAGE	NVARCHAR(2048)	= ERROR_MESSAGE(),
				@ERR_CODE		INT				= @ERR_FAILURE;
		
		IF	(@ERR_NUMBER >= 50000)	BEGIN
			IF	(@ERR_PROCEDURE = OBJECT_NAME(@@PROCID))
				SET	@ERR_CODE = @ERR_STATE;
		END
		
		IF	(@@NESTLEVEL = 1)
			RAISERROR(N'[%s], %s', @ERR_SEVERITY, @ERR_CODE, @ERR_PROCEDURE, @ERR_MESSAGE);
		ELSE
			RAISERROR(@ERR_MESSAGE, @ERR_SEVERITY, @ERR_CODE);
		
		RETURN	@ERR_CODE;
END CATCH
GO
