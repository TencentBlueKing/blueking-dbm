export default {
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
  mongo_user: ['read', 'readWrite', 'readAnyDatabase', 'readWriteAnyDatabase'],
  special_account: ['dba', 'apppdba', 'monitor', 'appmonitor'],
};
