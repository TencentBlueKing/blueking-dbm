DELETE FROM tb_config_name_def WHERE namespace = 'tendb' AND  conf_type = 'mysql_monitor' AND conf_file = 'items-config.yaml';
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'character-consistency', 'STRING', '{"role":[],"name":"character-consistency","schedule":"0 0 14 * * 1","enable":true,"machine_type":["single","backend","remote","spider"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'routine-definer', 'STRING', '{"role":[],"schedule":"0 0 15 * * 1","enable":true,"name":"routine-definer","machine_type":["single","backend","remote"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'view-definer', 'STRING', '{"enable":true,"schedule":"0 0 15 * * 1","name":"view-definer","role":[],"machine_type":["single","backend","remote"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'trigger-definer', 'STRING', '{"machine_type":["single","backend","remote"],"schedule":"0 0 15 * * 1","name":"trigger-definer","enable":true,"role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'engine', 'STRING', '{"role":[],"enable":true,"schedule":"0 0 12 * * *","name":"engine","machine_type":["single","backend","remote"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'ext3-check', 'STRING', '{"role":[],"schedule":"0 0 16 * * 1","name":"ext3-check","enable":true,"machine_type":["single","backend","remote"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'ibd-statistic', 'STRING', '{"role":["slave"],"schedule":"0 0 14 * * 1","name":"ibd-statistic","enable":true,"machine_type":["single","backend","remote"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'master-slave-heartbeat', 'STRING', '{"machine_type":["backend","remote"],"name":"master-slave-heartbeat","schedule":"@every 1m","enable":true,"role":["master","repeater","slave"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-config-diff', 'STRING', '{"machine_type":["single","backend","remote","spider"],"name":"mysql-config-diff","schedule":"0 5 10 * * *","enable":true,"role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-connlog-size', 'STRING', '{"role":[],"schedule":"0 0 12 * * *","name":"mysql-connlog-size","enable":true,"machine_type":["single","backend","remote","spider"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-connlog-rotate', 'STRING', '{"role":[],"schedule":"0 30 23 * * *","name":"mysql-connlog-rotate","enable":true,"machine_type":["single","backend","remote","spider"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-err-notice', 'STRING', '{"role":[],"enable":true,"schedule":"@every 1m","name":"mysql-err-notice","machine_type":["single","backend","remote"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-err-critical', 'STRING', '{"machine_type":["single","backend","remote"],"name":"mysql-err-critical","schedule":"@every 1m","enable":true,"role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'spider-err-notice', 'STRING', '{"machine_type":["spider"],"name":"spider-err-notice","schedule":"@every 1m","enable":true,"role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'spider-err-warn', 'STRING', '{"machine_type":["spider"],"role":[],"name":"spider-err-warn","schedule":"@every 1m","enable":true}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'spider-err-critical', 'STRING', '{"machine_type":["spider"],"role":[],"schedule":"@every 1m","enable":true,"name":"spider-err-critical"}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-lock', 'STRING', '{"role":[],"name":"mysql-lock","schedule":"@every 1m","enable":true,"machine_type":["single","backend","remote","spider"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-inject', 'STRING', '{"role":[],"name":"mysql-inject","schedule":"@every 1m","enable":true,"machine_type":["single","backend","spider"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'proxy-backend', 'STRING', '{"role":[],"schedule":"@every 1m","name":"proxy-backend","enable":true,"machine_type":["proxy"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'proxy-user-list', 'STRING', '{"machine_type":["proxy"],"schedule":"@every 1m","name":"proxy-user-list","enable":true,"role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'rotate-slowlog', 'STRING', '{"machine_type":["single","backend","remote","spider"],"role":[],"schedule":"0 55 23 * * *","enable":true,"name":"rotate-slowlog"}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'slave-status', 'STRING', '{"machine_type":["backend","remote"],"role":["slave","repeater"],"schedule":"@every 1m","name":"slave-status","enable":true}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'ctl-replicate', 'STRING', '{"machine_type":["spider"],"enable":true,"schedule":"@every 1m","name":"ctl-replicate","role":["spider_master"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'spider-remote', 'STRING', '{"machine_type":["spider"],"role":[],"enable":true,"schedule":"@every 1m","name":"spider-remote"}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'spider-table-schema-consistency', 'STRING', '{"role":["spider_master"],"name":"spider-table-schema-consistency","schedule":"0 10 1 * * *","enable":true,"machine_type":["spider"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'dbha-heartbeat', 'STRING', '{"schedule":"@every 1m","enable":true,"name":"dbha-heartbeat","role":[],"machine_type":["spider","remote","backend"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'unique-ctl-master', 'STRING', '{"machine_type":["spider"],"enable":true,"schedule":"@every 1m","name":"unique-ctl-master","role":["spider_master"]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'scene-snapshot', 'STRING', '{"machine_type":["spider","remote","backend","single"],"enable":false,"schedule":"@every 1m","name":"scene-snapshot","role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'mysql-timezone-change', 'STRING', '{"machine_type":["spider","remote","backend","single"],"role":[],"schedule":"@every 1m","name":"mysql-timezone-change","enable":true}', '', 'MAP', 1, 0, 0, 0, 1);
REPLACE INTO tb_config_name_def( namespace, conf_type, conf_file, conf_name, value_type, value_default, value_allowed, value_type_sub, flag_status, flag_disable, flag_locked, flag_encrypt, need_restart) VALUES( 'tendb', 'mysql_monitor', 'items-config.yaml', 'sys-timezone-change', 'STRING', '{"machine_type":["spider","proxy","remote","backend","single"],"schedule":"@every 1m","name":"sys-timezone-change","enable":true,"role":[]}', '', 'MAP', 1, 0, 0, 0, 1);
