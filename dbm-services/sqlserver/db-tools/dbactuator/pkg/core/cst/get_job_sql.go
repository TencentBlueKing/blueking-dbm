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

// GET_JOB_INFOS 获取实例的JOB信息的SQL
const GET_JOB_INFOS = `
SELECT a.job_id as job_id ,a.category_id as category_id 
FROM msdb.dbo.sysjobs a , msdb.dbo.syscategories c
WHERE    a.category_id = c.category_id 
AND a.name not like 'TC_%'
AND a.name not in('syspolicy_purge_history')
`

// GET_CREATE_JOB_SQL 拼接创建JOB的SQL
const GET_CREATE_JOB_SQL = `
DECLARE @i_enabled  TINYINT
DECLARE @sql VARCHAR(MAX)
DECLARE @i_job_name                    VARCHAR(1000)
DECLARE @i_notify_level_eventlog    INT
DECLARE @i_notify_level_email        INT
DECLARE @i_notify_level_netsend        INT
DECLARE @i_notify_level_page        INT
DECLARE @i_delete_level                INT
DECLARE @i_description                VARCHAR(1000)
DECLARE @i_category_name            VARCHAR(1000)
DECLARE @i_owner_login_name            VARCHAR(1000)
DECLARE @i_category_class            INT
DECLARE @i_start_step_id              INT                                
DECLARE @i_step_name                 VARCHAR(1000)      
DECLARE @i_step_id                     INT                
DECLARE @i_cmdexec_success_code        INT             
DECLARE @i_on_success_action         INT                
DECLARE @i_on_success_step_id         INT                
DECLARE @i_on_fail_action             INT                
DECLARE @i_on_fail_step_id             INT                
DECLARE @i_retry_attempts             BIGINT            
DECLARE @i_retry_interval             INT                
DECLARE @i_os_run_priority            INT                
DECLARE @i_subsystem                 VARCHAR(1000)      
DECLARE @i_command                    VARCHAR(8000)
DECLARE @i_database_name            VARCHAR(100)              
DECLARE @i_flags                    INT     
DECLARE @i_class VARCHAR(10) ,@i_type VARCHAR(10)
DECLARE @c_jobid UNIQUEIDENTIFIER ,@c_categoryid INT
DECLARE @loop_stepid                INT
DECLARE @m_stepid                    INT        
DECLARE @loop_scheduleid            INT
DECLARE @m_scheduleid                INT                 
DECLARE @i_schedule_enabled            TINYINT
DECLARE @i_freq_type                INT
DECLARE @i_schedule_name            VARCHAR(1000)    
DECLARE @i_freq_interval            INT    
DECLARE @i_freq_subday_type            INT
DECLARE @i_freq_subday_interval        INT
DECLARE @i_freq_relative_interval    INT
DECLARE @i_freq_recurrence_factor    INT
DECLARE @i_active_start_date        BIGINT    
DECLARE @i_active_end_date            BIGINT    
DECLARE @i_active_start_time        BIGINT    
DECLARE @i_active_end_time            BIGINT    
DECLARE @i_schedule_uid                VARCHAR(1000)
SET @i_class    =    'JOB'
SET @i_type        =    'LOCAL'
SET @c_jobid='%s'
SET @c_categoryid=%d
SET @sql = 'USE [msdb]'
SELECT  @i_job_name = a.name ,
        @i_enabled         = [enabled] ,
        @i_notify_level_eventlog = notify_level_eventlog ,
        @i_notify_level_email     = notify_level_email ,
        @i_notify_level_netsend     = notify_level_netsend ,
        @i_notify_level_page     = notify_level_page ,
        @i_delete_level             = delete_level ,
        @i_description             = [description] ,
        @i_category_name         = c.name ,
        @i_owner_login_name         =  ISNULL(SUSER_SNAME(a.owner_sid), N'''') ,
        @i_category_class         = category_class 
        FROM msdb.dbo.sysjobs a ,msdb.dbo.syscategories c
        WHERE a.category_id=c.category_id AND a.job_id=@c_jobid AND a.category_id = @c_categoryid
        
SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF NOT EXISTS (SELECT job_id FROM msdb.dbo.sysjobs_view WHERE name = N'''+@i_job_name+''')'
SET @sql=@sql+CHAR(13)+CHAR(10) + 'BEGIN'
SET @sql=@sql+CHAR(13)+CHAR(10) + 'BEGIN TRANSACTION' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'DECLARE @ReturnCode INT' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'SELECT @ReturnCode = 0'
SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF NOT EXISTS (SELECT name FROM msdb.dbo.syscategories WHERE name=N'''+ @i_category_name +''' AND category_class='+ CAST(@i_category_class AS VARCHAR) +' )' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'BEGIN' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC @ReturnCode = msdb.dbo.sp_add_category @class=N'''+ @i_class +''', @type=N'''+ @i_type +''', @name=N'''+ @i_category_name +'''' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback'
SET @sql=@sql+CHAR(13)+CHAR(10) + '' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'END'
SET @sql=@sql+CHAR(13)+CHAR(10) + ''
SET @sql=@sql+CHAR(13)+CHAR(10) + 'DECLARE @jobId BINARY(16)' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC @ReturnCode =  msdb.dbo.sp_add_job @job_name=N'''+ @i_job_name +''','  
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @enabled='+ CAST(@i_enabled AS VARCHAR) +',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @notify_level_eventlog='+ CAST(@i_notify_level_eventlog AS VARCHAR) +','
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @notify_level_email='+ CAST(@i_notify_level_email AS VARCHAR) +',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @notify_level_netsend='+ CAST(@i_notify_level_netsend AS VARCHAR) +',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @notify_level_page='+ CAST(@i_notify_level_page AS VARCHAR) +',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @delete_level='+ CAST(@i_delete_level AS VARCHAR) +',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @description=N'''+ @i_description +''',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @category_name=N'''+ @i_category_name +''',' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '        @owner_login_name=N'''+ @i_owner_login_name +''', @job_id = @jobId OUTPUT' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback' 
IF EXISTS ( SELECT TOP 1 1 FROM msdb.dbo.sysjobsteps WHERE job_id = @c_jobid )
BEGIN
    SELECT  @loop_stepid = MIN(step_id) ,@m_stepid = MAX(step_id) FROM msdb.dbo.sysjobsteps WHERE job_id = @c_jobid  
    WHILE (@loop_stepid < = @m_stepid) 
    BEGIN     
        SELECT    @i_start_step_id        = start_step_id,
                @i_step_name            = step_name ,
                @i_step_id                = step_id,
                @i_cmdexec_success_code = cmdexec_success_code ,
                @i_on_success_action    = on_success_action ,
                @i_on_success_step_id    = on_success_step_id ,
                @i_on_fail_action        = on_fail_action ,
                @i_on_fail_step_id        = on_fail_step_id ,
                @i_retry_attempts        = retry_attempts ,
                @i_retry_interval        = retry_interval ,
                @i_os_run_priority        = os_run_priority ,
                @i_subsystem            = subsystem ,
                @i_command                = command ,
                @i_database_name        = database_name ,
                @i_flags                = flags
                FROM msdb.dbo.sysjobs a ,msdb.dbo.sysjobsteps b 
                WHERE a.job_id = b.job_id AND step_id = @loop_stepid AND a.job_id = @c_jobid 
    
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC @ReturnCode = msdb.dbo.sp_add_jobstep @job_id=@jobId, @step_name=N'''+ @i_step_name +''',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @step_id='+ CAST(@i_step_id AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @cmdexec_success_code='+ CAST(@i_cmdexec_success_code AS VARCHAR) +','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @on_success_action='+ CAST(@i_on_success_action AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @on_success_step_id='+ CAST(@i_on_success_step_id AS VARCHAR) +','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @on_fail_action='+ CAST(@i_on_fail_action AS VARCHAR) +','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @on_fail_step_id='+ CAST(@i_on_fail_step_id AS VARCHAR) +','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @retry_attempts='+ CAST(@i_retry_attempts AS VARCHAR) +','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @retry_interval='+ CAST(@i_retry_interval AS VARCHAR) +','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @os_run_priority='+ CAST(@i_os_run_priority AS VARCHAR) +', @subsystem=N'''+ @i_subsystem +''','  
        SET @sql=@sql+CHAR(13)+CHAR(10) + ISNULL('        @command=N''' + REPLACE(@i_command ,'''' ,'''''') + ''',' ,'')  
        SET @sql=@sql+CHAR(13)+CHAR(10) + ISNULL('        @database_name=N'''+ @i_database_name +''',' ,'') 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @flags='+ CAST(@i_flags AS VARCHAR) 
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback' 
        
        SET @loop_stepid = ( SELECT TOP 1 step_id FROM msdb.dbo.sysjobsteps WHERE job_id = @c_jobid AND step_id > @loop_stepid ORDER BY step_id )
    END
END

SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC @ReturnCode = msdb.dbo.sp_update_job @job_id = @jobId, @start_step_id = '+ CAST(@i_start_step_id AS VARCHAR)  
SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback'  
IF EXISTS ( SELECT TOP 1 1 FROM msdb.dbo.sysschedules c ,msdb.dbo.sysjobschedules d WHERE c.schedule_id = d.schedule_id AND job_id = @c_jobid )
BEGIN
    SELECT @loop_scheduleid= MIN(c.schedule_id) ,@m_scheduleid = MAX(c.schedule_id) 
        FROM  msdb.dbo.sysschedules c ,msdb.dbo.sysjobschedules d
        WHERE c.schedule_id = d.schedule_id AND job_id = @c_jobid 
    WHILE ( @loop_scheduleid <= @m_scheduleid ) 
    BEGIN
        SELECT    @i_schedule_enabled            = [enabled] ,
                @i_freq_type                = freq_type ,
                @i_schedule_name            = name,
                @i_freq_interval            = freq_interval ,
                @i_freq_subday_type            = freq_subday_type ,
                @i_freq_subday_interval        = freq_subday_interval ,
                @i_freq_relative_interval    = freq_relative_interval ,
                @i_freq_recurrence_factor    = freq_recurrence_factor ,
                @i_active_start_date        = active_start_date ,
                @i_active_end_date            = active_end_date ,
                @i_active_start_time        = active_start_time ,
                @i_active_end_time            = active_end_time ,
                @i_schedule_uid                = schedule_uid 
                FROM msdb.dbo.sysschedules c LEFT JOIN msdb.dbo.sysjobschedules d
                        ON c.schedule_id = d.schedule_id 
                WHERE d.job_id = @c_jobid AND c.schedule_id = @loop_scheduleid  

        SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC @ReturnCode = msdb.dbo.sp_add_jobschedule @job_id=@jobId, @name=N'''+ @i_schedule_name +''',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @enabled='+ CAST(@i_schedule_enabled AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @freq_type='+ CAST(@i_freq_type AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @freq_interval='+ CAST(@i_freq_interval AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @freq_subday_type='+ CAST(@i_freq_subday_type AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @freq_subday_interval='+ CAST(@i_freq_subday_interval AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @freq_relative_interval='+ CAST(@i_freq_relative_interval AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @freq_recurrence_factor='+ CAST(@i_freq_recurrence_factor AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @active_start_date='+ CAST(@i_active_start_date AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @active_end_date='+ CAST(@i_active_end_date AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @active_start_time='+ CAST(@i_active_start_time AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @active_end_time='+ CAST(@i_active_end_time AS VARCHAR) +',' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + '        @schedule_uid=N'''+ @i_schedule_uid +'''' 
        SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback' 
        
        SET @loop_scheduleid = ( SELECT TOP 1 c.schedule_id FROM msdb.dbo.sysschedules c ,msdb.dbo.sysjobschedules d
                                        WHERE c.schedule_id = d.schedule_id AND job_id = @c_jobid AND c.schedule_id > @loop_scheduleid )  
    END
END

SET @sql=@sql+CHAR(13)+CHAR(10) + 'EXEC @ReturnCode = msdb.dbo.sp_add_jobserver @job_id = @jobId, @server_name = N''(local)''' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'IF (@@ERROR <> 0 OR @ReturnCode <> 0) GOTO QuitWithRollback' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'COMMIT TRANSACTION' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'GOTO EndSave' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'QuitWithRollback:' 
SET @sql=@sql+CHAR(13)+CHAR(10) + '    IF (@@TRANCOUNT > 0) ROLLBACK TRANSACTION' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'EndSave:' 
SET @sql=@sql+CHAR(13)+CHAR(10) + 'END' 
select @sql as job_sql
`
