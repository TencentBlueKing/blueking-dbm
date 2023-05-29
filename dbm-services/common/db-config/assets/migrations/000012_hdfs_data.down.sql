DELETE FROM tb_config_file_def WHERE namespace='hdfs';
DELETE FROM tb_config_name_def WHERE namespace='hdfs' AND (flag_encrypt!=1 or value_default like '{{%');
