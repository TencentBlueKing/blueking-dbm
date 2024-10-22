export default {
  mongo_user: ['Read', 'readWrite', 'readAnyDatabase', 'readWriteAnyDatabase'],
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
};
