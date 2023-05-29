DELETE FROM tb_config_file_def WHERE namespace='TwemproxyTendisSSDInstance';
DELETE FROM tb_config_name_def WHERE namespace='TwemproxyTendisSSDInstance' AND (flag_encrypt!=1 or value_default like '{{%');
