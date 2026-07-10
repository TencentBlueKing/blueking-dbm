with cf_split as (
    select substr(cf, 1, instr(cf, '/', -1) - 1) as dir
    from (
             select trim(regexp_substr(value, '[^,]+', 1, level)) as cf
             from v$parameter
             where name = 'control_files'
                 connect by level <= regexp_count(value, ',') + 1
         )
),
     file_dirs as (
         select substr(name,   1, instr(name,   '/', -1) - 1) as dir from v$datafile
         union
         select substr(name,   1, instr(name,   '/', -1) - 1)        from v$tempfile
         union
         select substr(member, 1, instr(member, '/', -1) - 1)        from v$logfile
         union
         select substr(name,   1, instr(name,   '/', -1) - 1)        from v$controlfile
     ),
     param_dirs as (
         select value as dir
         from v$parameter
         where name in ('audit_file_dest','diagnostic_dest','db_recovery_file_dest',
                        'db_create_file_dest','db_create_online_log_dest_1',
                        'db_create_online_log_dest_2','db_create_online_log_dest_3',
                        'db_create_online_log_dest_4','db_create_online_log_dest_5')
           and value is not null
         union
         select regexp_replace(regexp_substr(upper(value),'LOCATION=[^ ,]+'),'LOCATION=','')
         from v$parameter
         where name like 'log_archive_dest\_%' escape '\'
             and value is not null
             and upper(value) like '%LOCATION=%'
     )
select dir from param_dirs where upper(dir) != 'USE_DB_RECOVERY_FILE_DEST'
union
select dir from cf_split
union
select dir from file_dirs
order by 1