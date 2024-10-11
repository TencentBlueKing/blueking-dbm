import { AccountTypes } from '@common/const';

export default {
  [AccountTypes.MYSQL]: {
    dbOperations: {
      dml: ['select', 'insert', 'update', 'delete', 'show view'],
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
      glob: ['file', 'reload', 'show databases', 'process', 'replication slave', 'replication client'],
    },
    ddlSensitiveWords: ['trigger', 'event', 'create routine', 'alter routine', 'references', 'create temporary tables'],
  },
  [AccountTypes.TENDBCLUSTER]: {
    dbOperations: {
      dml: ['select', 'insert', 'update', 'delete'],
      ddl: ['execute'],
      glob: ['file', 'reload', 'process', 'show databases'],
    },
    ddlSensitiveWords: [],
  },
};
