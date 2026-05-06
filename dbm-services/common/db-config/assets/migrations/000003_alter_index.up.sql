ALTER TABLE tb_config_node
      ADD INDEX `idx_namespace`(`namespace`,`conf_file`,`conf_name`),
      ADD INDEX `idx_level` (`level_name`,`level_value`,`conf_file`),
      ADD INDEX `idx_confname` (`conf_name`);