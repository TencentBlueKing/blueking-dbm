DELETE FROM tb_config_file_def WHERE namespace='tendbha';
DELETE FROM tb_config_name_def WHERE namespace='tendbha' AND (flag_encrypt!=1 or value_default like '{{%');
