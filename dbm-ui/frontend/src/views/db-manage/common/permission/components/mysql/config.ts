import { AccountTypes } from '@common/const';

const SPECIAL_ACCOUNT = [
  'gcs_admin',
  'gcs_dba',
  'MONITOR',
  'GM',
  'ADMIN',
  'repl',
  'dba_bak_all_sel',
  'yw',
  'partition_yw',
  'spider',
  'mysql.session',
  'mysql.sys',
  'gcs_spider',
  'sync',
];

export default {
  [AccountTypes.MYSQL]: {
    dbOperations: {
      ddl: [
        'create',
        'alter',
        'drop',
        'index',
        'create view',
        'execute',
        'trigger',
        'event',
        'create routine',
        'alter routine',
        'references',
        'create temporary tables',
      ],
      dml: ['select', 'insert', 'update', 'delete', 'show view'],
      glob: ['file', 'reload', 'show databases', 'process', 'replication slave', 'replication client'],
    },
    ddlSensitiveWords: ['trigger', 'event', 'create routine', 'alter routine', 'references', 'create temporary tables'],
    special_account: SPECIAL_ACCOUNT,
  },
  [AccountTypes.TENDBCLUSTER]: {
    dbOperations: {
      ddl: ['execute'],
      dml: ['select', 'insert', 'update', 'delete'],
      glob: ['file', 'reload', 'process', 'show databases'],
    },
    ddlSensitiveWords: [],
    special_account: SPECIAL_ACCOUNT,
  },
};
