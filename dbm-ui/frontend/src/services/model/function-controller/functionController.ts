/* eslint-disable max-len */
/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import { ClusterTypes } from '@common/const';

export type AddonsFunctions = 'redis_nameservice';
export type MySQLFunctions = 'toolbox' | 'tendbsingle' | 'tendbha' | 'tendbcluster' | 'tendbcluster_toolbox';
export type RedisFunctions =
  | 'PredixyTendisplusCluster'
  | 'TwemproxyRedisInstance'
  | 'TwemproxyTendisSSDInstance'
  | 'PredixyRedisCluster'
  | 'RedisInstance'
  | 'toolbox';
export type BigdataFunctions = 'es' | 'kafka' | 'hdfs' | 'influxdb' | 'pulsar' | 'riak';
export type MonitorFunctions = 'duty_rule' | 'monitor_policy' | 'notice_group';
export type MongoFunctions = 'mongodb';
export type SqlServerFunctions = 'sqlserverCluster' | 'sqlserver_single' | 'sqlserver_ha';
export type FunctionKeys =
  | AddonsFunctions
  | MySQLFunctions
  | RedisFunctions
  | BigdataFunctions
  | MonitorFunctions
  | SqlServerFunctions
  | MongoFunctions;
export type FunctionTabId = FunctionKeys | ClusterTypes.MONGO_REPLICA_SET | ClusterTypes.MONGO_SHARED_CLUSTER;

export interface ControllerBaseInfo {
  is_enabled: boolean;
}

interface ControllerItem<T extends string> extends ControllerBaseInfo {
  children: Record<T, ControllerBaseInfo>;
}

interface ControllerData {
  addons: ControllerItem<AddonsFunctions>;
  mysql: ControllerItem<MySQLFunctions>;
  redis: ControllerItem<RedisFunctions>;
  bigdata: ControllerItem<BigdataFunctions>;
  monitor: ControllerItem<MonitorFunctions>;
  mongodb: ControllerItem<MongoFunctions>;
  sqlserver: ControllerItem<SqlServerFunctions>;
  riak: ControllerItem<SqlServerFunctions>;
  personalWorkbench: ControllerItem<string>;
  'personalWorkbench.serviceApply': ControllerItem<string>;
  'personalWorkbench.myTickets': ControllerItem<string>;
  'personalWorkbench.myTodos': ControllerItem<string>;
  observableManage: ControllerItem<string>;
  'observableManage.DBHASwitchEvents': ControllerItem<string>;
  'observableManage.healthReport': ControllerItem<string>;
  globalConfigManage: ControllerItem<string>;
  'globalConfigManage.dbConfig': ControllerItem<string>;
  'globalConfigManage.versionFile': ControllerItem<string>;
  'globalConfigManage.monitorStrategy': ControllerItem<string>;
  'globalConfigManage.rotationManage': ControllerItem<string>;
  'globalConfigManage.passwordSafe': ControllerItem<string>;
  'globalConfigManage.staffManage': ControllerItem<string>;
  'globalConfigManage.ticketFlowSetting': ControllerItem<string>;
  'globalConfigManage.alarmGroup': ControllerItem<string>;
  'globalConfigManage.whitelistManage': ControllerItem<string>;
  resourceManage: ControllerItem<string>;
  'resourceManage.resourceSpec': ControllerItem<string>;
  'resourceManage.resourcePool': ControllerItem<string>;
  'resourceManage.dirtyHostManage': ControllerItem<string>;
  'resourceManage.resourceOperationRecord': ControllerItem<string>;
  bizConfigManage: ControllerItem<string>;
  'bizConfigManage.monitorStrategy': ControllerItem<string>;
  'bizConfigManage.alarmGroup': ControllerItem<string>;
  'bizConfigManage.dbConfigure': ControllerItem<string>;
  'bizConfigManage.StaffManage': ControllerItem<string>;
  databaseManage: ControllerItem<string>;
  'databaseManage.missionManage': ControllerItem<string>;
  'databaseManage.whitelistManage': ControllerItem<string>;
  'databaseManage.temporaryPaasswordModify': ControllerItem<string>;
  'mysql.haInstanceList': ControllerItem<string>;
  'mysql.dataSubscription': ControllerItem<string>;
  'mysql.permissionManage': ControllerItem<string>;
  'mysql.partitionManage': ControllerItem<string>;
  'mysql.toolbox.sqlExecute': ControllerItem<string>;
  'mysql.toolbox.dbRename': ControllerItem<string>;
  'mysql.toolbox.rollback': ControllerItem<string>;
  'mysql.toolbox.flashback': ControllerItem<string>;
  'mysql.toolbox.dbTableBackup': ControllerItem<string>;
  'mysql.toolbox.dbBackup': ControllerItem<string>;
  'mysql.toolbox.clientPermissionClone': ControllerItem<string>;
  'mysql.toolbox.dbInstancePermissionClone': ControllerItem<string>;
  'mysql.toolbox.slaveRebuild': ControllerItem<string>;
  'mysql.toolbox.slaveAdd': ControllerItem<string>;
  'mysql.toolbox.masterSlaveClone': ControllerItem<string>;
  'mysql.toolbox.masterSlaveSwap': ControllerItem<string>;
  'mysql.toolbox.proxyReplace': ControllerItem<string>;
  'mysql.toolbox.proxyAdd': ControllerItem<string>;
  'mysql.toolbox.masterFailover': ControllerItem<string>;
  'mysql.toolbox.dbClear': ControllerItem<string>;
  'mysql.toolbox.checksum': ControllerItem<string>;
  'mysql.toolbox.openareaTemplate': ControllerItem<string>;
  'tendbCluster.clusterManage.proxyScaleUp': ControllerItem<string>;
  'tendbCluster.clusterManage.proxyScaleDown': ControllerItem<string>;
  'tendbCluster.clusterManage.removeMNTNode': ControllerItem<string>;
  'tendbCluster.clusterManage.removeReadonlyNode': ControllerItem<string>;
  'tendbCluster.clusterManage.disable': ControllerItem<string>;
  'tendbCluster.instanceManage': ControllerItem<string>;
  'tendbCluster.partitionManage': ControllerItem<string>;
  'tendbCluster.permissionManage': ControllerItem<string>;
  'tendbCluster.toolbox.sqlExecute': ControllerItem<string>;
  'tendbCluster.toolbox.dbRename': ControllerItem<string>;
  'tendbCluster.toolbox.rollback': ControllerItem<string>;
  'tendbCluster.toolbox.rollbackRecord': ControllerItem<string>;
  'tendbCluster.toolbox.flashback': ControllerItem<string>;
  'tendbCluster.toolbox.dbTableBackup': ControllerItem<string>;
  'tendbCluster.toolbox.dbBackup': ControllerItem<string>;
  'tendbCluster.toolbox.clientPermissionClone': ControllerItem<string>;
  'tendbCluster.toolbox.dbInstancePermissionClone': ControllerItem<string>;
  'tendbCluster.toolbox.addMnt': ControllerItem<string>;
  'tendbCluster.toolbox.proxySlaveApply': ControllerItem<string>;
  'tendbCluster.toolbox.masterSlaveSwap': ControllerItem<string>;
  'tendbCluster.toolbox.masterFailover': ControllerItem<string>;
  'tendbCluster.toolbox.capacityChange': ControllerItem<string>;
  'tendbCluster.toolbox.proxyScaleDown': ControllerItem<string>;
  'tendbCluster.toolbox.proxyScaleUp': ControllerItem<string>;
  'tendbCluster.toolbox.dbClear': ControllerItem<string>;
  'tendbCluster.toolbox.checksum': ControllerItem<string>;
  'tendbCluster.toolbox.openareaTemplate': ControllerItem<string>;
  'tendbCluster.toolbox.slaveRebuild': ControllerItem<string>;
  'tendbCluster.toolbox.masterSlaveClone': ControllerItem<string>;
  'redis.clusterManage.getAccess': ControllerItem<string>;
  'redis.clusterManage.enableCLB': ControllerItem<string>;
  'redis.clusterManage.DNSDomainToCLB': ControllerItem<string>;
  'redis.clusterManage.enablePolaris': ControllerItem<string>;
  'redis.clusterManage.disable': ControllerItem<string>;
  'redis.clusterManage.enable': ControllerItem<string>;
  'redis.clusterManage.delete': ControllerItem<string>;
  'redis.instanceManage': ControllerItem<string>;
  'redis.haClusterManage': ControllerItem<string>;
  'redis.haInstanceManage': ControllerItem<string>;
  'redis.toolbox.capacityChange': ControllerItem<string>;
  'redis.toolbox.proxyScaleUp': ControllerItem<string>;
  'redis.toolbox.proxyScaleDown': ControllerItem<string>;
  'redis.toolbox.clusterShardChange': ControllerItem<string>;
  'redis.toolbox.clusterTypeChange': ControllerItem<string>;
  'redis.toolbox.slaveRebuild': ControllerItem<string>;
  'redis.toolbox.masterSlaveSwap': ControllerItem<string>;
  'redis.toolbox.dbReplace': ControllerItem<string>;
  'redis.toolbox.versionUpgrade': ControllerItem<string>;
  'redis.toolbox.rollback': ControllerItem<string>;
  'redis.toolbox.rollbackRecord': ControllerItem<string>;
  'redis.toolbox.recoverFromInstance': ControllerItem<string>;
  'redis.toolbox.dataCopy': ControllerItem<string>;
  'redis.toolbox.dataCopyRecord': ControllerItem<string>;

}

export type ExtractedControllerDataKeys = Extract<keyof ControllerData, string>;

export default class FunctionController {
  addons: ControllerItem<AddonsFunctions>;
  mysql: ControllerItem<MySQLFunctions>;
  redis: ControllerItem<RedisFunctions>;
  bigdata: ControllerItem<BigdataFunctions>;
  monitor: ControllerItem<MonitorFunctions>;
  mongodb: ControllerItem<MongoFunctions>;
  sqlserver: ControllerItem<SqlServerFunctions>;
  riak: ControllerItem<SqlServerFunctions>;

  // dbconsole 路由有关的开关
  personalWorkbench: ControllerItem<string>;
  'personalWorkbench.serviceApply': ControllerItem<string>;
  'personalWorkbench.myTickets': ControllerItem<string>;
  'personalWorkbench.myTodos': ControllerItem<string>;
  observableManage: ControllerItem<string>;
  'observableManage.DBHASwitchEvents': ControllerItem<string>;
  'observableManage.healthReport': ControllerItem<string>;
  globalConfigManage: ControllerItem<string>;
  'globalConfigManage.dbConfig': ControllerItem<string>;
  'globalConfigManage.versionFile': ControllerItem<string>;
  'globalConfigManage.monitorStrategy': ControllerItem<string>;
  'globalConfigManage.rotationManage': ControllerItem<string>;
  'globalConfigManage.passwordSafe': ControllerItem<string>;
  'globalConfigManage.staffManage': ControllerItem<string>;
  'globalConfigManage.ticketFlowSetting': ControllerItem<string>;
  'globalConfigManage.alarmGroup': ControllerItem<string>;
  'globalConfigManage.whitelistManage': ControllerItem<string>;
  resourceManage: ControllerItem<string>;
  'resourceManage.resourceSpec': ControllerItem<string>;
  'resourceManage.resourcePool': ControllerItem<string>;
  'resourceManage.dirtyHostManage': ControllerItem<string>;
  'resourceManage.resourceOperationRecord': ControllerItem<string>;
  bizConfigManage: ControllerItem<string>;
  'bizConfigManage.monitorStrategy': ControllerItem<string>;
  'bizConfigManage.alarmGroup': ControllerItem<string>;
  'bizConfigManage.dbConfigure': ControllerItem<string>;
  'bizConfigManage.StaffManage': ControllerItem<string>;
  databaseManage: ControllerItem<string>;
  'databaseManage.missionManage': ControllerItem<string>;
  'databaseManage.whitelistManage': ControllerItem<string>;
  'databaseManage.temporaryPaasswordModify': ControllerItem<string>;
  'mysql.haInstanceList': ControllerItem<string>;
  'mysql.dataSubscription': ControllerItem<string>;
  'mysql.permissionManage': ControllerItem<string>;
  'mysql.partitionManage': ControllerItem<string>;
  'mysql.toolbox.sqlExecute': ControllerItem<string>;
  'mysql.toolbox.dbRename': ControllerItem<string>;
  'mysql.toolbox.rollback': ControllerItem<string>;
  'mysql.toolbox.flashback': ControllerItem<string>;
  'mysql.toolbox.dbTableBackup': ControllerItem<string>;
  'mysql.toolbox.dbBackup': ControllerItem<string>;
  'mysql.toolbox.clientPermissionClone': ControllerItem<string>;
  'mysql.toolbox.dbInstancePermissionClone': ControllerItem<string>;
  'mysql.toolbox.slaveRebuild': ControllerItem<string>;
  'mysql.toolbox.slaveAdd': ControllerItem<string>;
  'mysql.toolbox.masterSlaveClone': ControllerItem<string>;
  'mysql.toolbox.masterSlaveSwap': ControllerItem<string>;
  'mysql.toolbox.proxyReplace': ControllerItem<string>;
  'mysql.toolbox.proxyAdd': ControllerItem<string>;
  'mysql.toolbox.masterFailover': ControllerItem<string>;
  'mysql.toolbox.dbClear': ControllerItem<string>;
  'mysql.toolbox.checksum': ControllerItem<string>;
  'mysql.toolbox.openareaTemplate': ControllerItem<string>;
  'tendbCluster.clusterManage.proxyScaleUp': ControllerItem<string>;
  'tendbCluster.clusterManage.proxyScaleDown': ControllerItem<string>;
  'tendbCluster.clusterManage.removeMNTNode': ControllerItem<string>;
  'tendbCluster.clusterManage.removeReadonlyNode': ControllerItem<string>;
  'tendbCluster.clusterManage.disable': ControllerItem<string>;
  'tendbCluster.instanceManage': ControllerItem<string>;
  'tendbCluster.partitionManage': ControllerItem<string>;
  'tendbCluster.permissionManage': ControllerItem<string>;
  'tendbCluster.toolbox.sqlExecute': ControllerItem<string>;
  'tendbCluster.toolbox.dbRename': ControllerItem<string>;
  'tendbCluster.toolbox.rollback': ControllerItem<string>;
  'tendbCluster.toolbox.rollbackRecord': ControllerItem<string>;
  'tendbCluster.toolbox.flashback': ControllerItem<string>;
  'tendbCluster.toolbox.dbTableBackup': ControllerItem<string>;
  'tendbCluster.toolbox.dbBackup': ControllerItem<string>;
  'tendbCluster.toolbox.clientPermissionClone': ControllerItem<string>;
  'tendbCluster.toolbox.dbInstancePermissionClone': ControllerItem<string>;
  'tendbCluster.toolbox.addMnt': ControllerItem<string>;
  'tendbCluster.toolbox.proxySlaveApply': ControllerItem<string>;
  'tendbCluster.toolbox.masterSlaveSwap': ControllerItem<string>;
  'tendbCluster.toolbox.masterFailover': ControllerItem<string>;
  'tendbCluster.toolbox.capacityChange': ControllerItem<string>;
  'tendbCluster.toolbox.proxyScaleDown': ControllerItem<string>;
  'tendbCluster.toolbox.proxyScaleUp': ControllerItem<string>;
  'tendbCluster.toolbox.dbClear': ControllerItem<string>;
  'tendbCluster.toolbox.checksum': ControllerItem<string>;
  'tendbCluster.toolbox.openareaTemplate': ControllerItem<string>;
  'tendbCluster.toolbox.slaveRebuild': ControllerItem<string>;
  'tendbCluster.toolbox.masterSlaveClone': ControllerItem<string>;
  'redis.clusterManage.getAccess': ControllerItem<string>;
  'redis.clusterManage.enableCLB': ControllerItem<string>;
  'redis.clusterManage.DNSDomainToCLB': ControllerItem<string>;
  'redis.clusterManage.enablePolaris': ControllerItem<string>;
  'redis.clusterManage.disable': ControllerItem<string>;
  'redis.clusterManage.enable': ControllerItem<string>;
  'redis.clusterManage.delete': ControllerItem<string>;
  'redis.instanceManage': ControllerItem<string>;
  'redis.haClusterManage': ControllerItem<string>;
  'redis.haInstanceManage': ControllerItem<string>;
  'redis.toolbox.capacityChange': ControllerItem<string>;
  'redis.toolbox.proxyScaleUp': ControllerItem<string>;
  'redis.toolbox.proxyScaleDown': ControllerItem<string>;
  'redis.toolbox.clusterShardChange': ControllerItem<string>;
  'redis.toolbox.clusterTypeChange': ControllerItem<string>;
  'redis.toolbox.slaveRebuild': ControllerItem<string>;
  'redis.toolbox.masterSlaveSwap': ControllerItem<string>;
  'redis.toolbox.dbReplace': ControllerItem<string>;
  'redis.toolbox.versionUpgrade': ControllerItem<string>;
  'redis.toolbox.rollback': ControllerItem<string>;
  'redis.toolbox.rollbackRecord': ControllerItem<string>;
  'redis.toolbox.recoverFromInstance': ControllerItem<string>;
  'redis.toolbox.dataCopy': ControllerItem<string>;
  'redis.toolbox.dataCopyRecord': ControllerItem<string>;

  constructor(payload = {} as ControllerData) {
    this.addons = payload.addons;
    this.mysql = payload.mysql;
    this.redis = payload.redis;
    this.mongodb = payload.mongodb;
    this.bigdata = payload.bigdata;
    this.monitor = payload.monitor;
    this.sqlserver = payload.sqlserver;
    this.riak = payload.riak;

    this.personalWorkbench = payload.personalWorkbench;
    this.observableManage = payload.observableManage;
    this.globalConfigManage = payload.globalConfigManage;
    this.resourceManage = payload.resourceManage;
    this.bizConfigManage = payload.bizConfigManage;
    this.databaseManage = payload.databaseManage;

    // 批处理 dbconsole 的开关
    Object.assign(this, payload);
  }

  getFlatData<T extends FunctionKeys, K extends ExtractedControllerDataKeys>(key: K) {
    const item = this[key] as ControllerItem<T>;

    if (!item) {
      return {} as Record<T | K, boolean>;
    }

    const flatData = {
      [key]: item.is_enabled,
    } as Record<T | K, boolean>;

    const { children } = item;
    const keys = Object.keys(children) as T[];
    return keys.reduce((res, childKey) => {
      res[childKey] = children[childKey].is_enabled;
      return res;
    }, flatData);
  }
}
