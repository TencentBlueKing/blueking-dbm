export default {
  mongo_user: ['read', 'readWrite', 'readAnyDatabase', 'readWriteAnyDatabase'],
  mongo_manager: [
    'dbAdmin',
    'backup',
    'restore',
    'userAdmin',
    'clusterAdmin',
    'clusterManager',
    'clusterMonitor',
    'hostManager',
    'userAdminAnyDatabase',
    'dbAdminAnyDatabase',
    'dbOwner',
    'root',
  ],
  special_account: ['dba', 'apppdba', 'monitor', 'appmonitor'],
};
