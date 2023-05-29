DELETE FROM tb_config_file_def WHERE namespace='TendisX';
DELETE FROM tb_config_name_def WHERE namespace='TendisX' AND (flag_encrypt!=1 or value_default like '{{%');
