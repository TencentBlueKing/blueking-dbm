DELETE FROM tb_config_file_def WHERE namespace='sqlserver_single';
DELETE FROM tb_config_name_def WHERE namespace='sqlserver_single' AND (flag_encrypt!=1 or value_default like '{{%');
