ALTER TABLE tb_config_name_def DROP COLUMN `stage`;
ALTER TABLE tb_config_name_def ADD COLUMN `deleted` tinyint(4) NOT NULL DEFAULT '0'
