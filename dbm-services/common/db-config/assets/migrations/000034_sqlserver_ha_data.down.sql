DELETE FROM tb_config_file_def WHERE namespace='sqlserver_ha';
DELETE FROM tb_config_name_def WHERE namespace='sqlserver_ha' AND (flag_encrypt!=1 or value_default like '{{%');
