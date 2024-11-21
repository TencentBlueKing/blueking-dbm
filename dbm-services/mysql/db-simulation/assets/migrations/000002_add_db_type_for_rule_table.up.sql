ALTER TABLE tb_syntax_rules
ADD COLUMN `db_type` varchar(64) NOT NULL DEFAULT ''
AFTER `id`;
ALTER TABLE tb_syntax_rules DROP INDEX `group`;
ALTER TABLE tb_syntax_rules
ADD UNIQUE INDEX `group`(`group_name`, `db_type`, `rule_name`);