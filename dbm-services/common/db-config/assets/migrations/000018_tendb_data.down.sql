DELETE FROM tb_config_file_def WHERE namespace='tendb';
DELETE FROM tb_config_name_def WHERE namespace='tendb' AND (flag_encrypt!=1 or value_default like '{{%');
