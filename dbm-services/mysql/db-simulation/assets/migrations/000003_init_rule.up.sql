delete from tb_syntax_rules;
INSERT INTO `tb_syntax_rules`
VALUES (
        1,
        'mysql',
        'CommandRule',
        'HighRiskCommandRule',
        '[\"drop_table\", \"drop_index\", \"lock_tables\", \"drop_db\", \"analyze\",\"rename_table\",\"drop_procedure\", \"drop_view\",\"drop_trigger\",\"drop_function\", \"drop_server\",\"drop_event\", \"drop_compression_dictionary\",\"optimize\", \"alter_tablespace\"]',
        'arry',
        'Val in Item',
        '高危命令',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        2,
        'mysql',
        'CommandRule',
        'BanCommandRule',
        '[\"truncate\", \"revoke\", \"kill\", \"reset\", \"drop_user\", \"grant\",\"create_user\", \"revoke_all\", \"shutdown\", \"lock_tables_for_backup\",\"reset\", \"purge\", \"lock_binlog_for_backup\",\"lock_tables_for_backup\",\"install_plugin\", \"uninstall_plugin\",\"alter_user\"]',
        'arry',
        'Val in Item',
        '高危变更类型',
        1,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        3,
        'mysql',
        'CreateTableRule',
        'SuggestBlobColumCount',
        '10',
        'int',
        'Val >= Item ',
        '建议单表Blob字段不要过多',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        4,
        'mysql',
        'CreateTableRule',
        'SuggestEngine',
        '\"innodb\"',
        'string',
        'not (Val contains Item) and ( len(Val) != 0 )',
        '建议使用Innodb表',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        5,
        'mysql',
        'CreateTableRule',
        'NeedPrimaryKey',
        '1',
        'int',
        'Val == Item',
        '建议包含主键',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        6,
        'mysql',
        'CreateTableRule',
        'DefinerRule',
        '[\"ADMIN@localhost\"]',
        'arry',
        'Val not in Item ',
        '必须指定definer',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        7,
        'mysql',
        'CreateTableRule',
        'NormalizedName',
        '[\"first_char_exception\", \"special_char\", \"Keyword_exception\"]',
        'arry',
        'Val in Item ',
        '规范化命名',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        8,
        'mysql',
        'AlterTableRule',
        'HighRiskType',
        '[\"drop_column\"]',
        'arry',
        'Val in Item',
        '高危变更类型',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        9,
        'mysql',
        'AlterTableRule',
        'HighRiskPkAlterType',
        '[\"add_column\", \"add_key\", \"change_column\"]',
        'arry',
        'Val in Item',
        '主键高危变更类型',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        10,
        'mysql',
        'AlterTableRule',
        'AlterUseAfter',
        '\"\"',
        'string',
        'Val != Item',
        '变更表时使用了after',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        11,
        'mysql',
        'AlterTableRule',
        'AddColumnMixed',
        '\"add_column\"',
        'string',
        '( Item in Val ) && ( len(Val) > 1 )',
        '加字段和其它alter table 类型混用，可能导致非在线加字段',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        12,
        'mysql',
        'DmlRule',
        'DmlNotHasWhere',
        'true',
        'bool',
        ' Val != Item ',
        '没有使用WHERE或者LIMIT,可能会导致全表数据更改',
        0,
        0
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        13,
        'spider',
        'CommandRule',
        'HighRiskCommandRule',
        '[\"truncate\",\"drop_table\", \"drop_index\", \"lock_tables\", \"drop_db\", \"analyze\",\"rename_table\",\"drop_procedure\", \"drop_view\",\"drop_trigger\",\"drop_function\", \"drop_server\",\"drop_event\", \"drop_compression_dictionary\",\"optimize\", \"alter_tablespace\"]',
        'arry',
        'Val in Item',
        '高危命令',
        0,
        1
    );
INSERT INTO `tb_syntax_rules`
VALUES (
        14,
        'spider',
        'CommandRule',
        'BanCommandRule',
        '[\"revoke\", \"kill\", \"reset\", \"drop_user\", \"grant\",\"create_user\", \"revoke_all\", \"shutdown\", \"lock_tables_for_backup\",\"reset\", \"purge\", \"lock_binlog_for_backup\",\"lock_tables_for_backup\",\"install_plugin\", \"uninstall_plugin\",\"alter_user\",\"slave_start\",\"slave_stop\",\"change_master\",\"start_group_replication\",\"stop_group_replication\",\"change_replication_filter\"]',
        'arry',
        'Val in Item',
        '禁止的变更类型',
        1,
        1
    );