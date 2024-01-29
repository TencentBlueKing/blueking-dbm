DELETE FROM tb_config_file_def WHERE namespace='sqlserver';
DELETE FROM tb_config_name_def WHERE namespace='sqlserver' AND (flag_encrypt!=1 or value_default like '{{%');
