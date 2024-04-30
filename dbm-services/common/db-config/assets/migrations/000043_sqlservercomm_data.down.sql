DELETE FROM tb_config_file_def WHERE namespace='sqlservercomm';
DELETE FROM tb_config_name_def WHERE namespace='sqlservercomm' AND (flag_encrypt!=1 or value_default like '{{%');
