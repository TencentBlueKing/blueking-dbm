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

export type AddonsFunctions = 'redis_nameservice';
export type MySQLFunctions = 'toolbox' | 'tendbsingle' | 'tendbha' | 'tendbcluster' | 'tendbcluster_toolbox';
export type RedisFunctions = 'PredixyTendisplusCluster' | 'TwemproxyRedisInstance' | 'TwemproxyTendisSSDInstance' | 'toolbox';
export type BigdataFunctions = 'es' | 'kafka' | 'hdfs' | 'influxdb' | 'pulsar' | 'riak';
export type MonitorFunctions = 'duty_rule' | 'monitor_policy' | 'notice_group';
export type MongoFunctions = 'mongodb';
export type FunctionKeys = AddonsFunctions | MySQLFunctions | RedisFunctions | BigdataFunctions | MonitorFunctions | MongoFunctions

export interface ControllerBaseInfo {
  is_enabled: boolean,
}

interface ControllerItem<T extends string> extends ControllerBaseInfo {
  children: Record<T, ControllerBaseInfo>
}

interface ControllerData {
  addons: ControllerItem<AddonsFunctions>,
  mysql: ControllerItem<MySQLFunctions>,
  redis: ControllerItem<RedisFunctions>,
  bigdata: ControllerItem<BigdataFunctions>,
  monitor: ControllerItem<MonitorFunctions>,
  mongodb: ControllerItem<MongoFunctions>,
}

export type ExtractedControllerDataKeys = Extract<keyof ControllerData, string>;

export default class FunctionController {
  addons: ControllerItem<AddonsFunctions>;
  mysql: ControllerItem<MySQLFunctions>;
  redis: ControllerItem<RedisFunctions>;
  bigdata: ControllerItem<BigdataFunctions>;
  monitor: ControllerItem<MonitorFunctions>;
  mongodb: ControllerItem<MongoFunctions>;

  constructor(payload = {} as ControllerData) {
    this.addons = payload.addons;
    this.mysql = payload.mysql;
    this.redis = payload.redis;
    this.bigdata = payload.bigdata;
    this.monitor = payload.monitor;
    this.mongodb = payload.mongodb;
  }

  getFlatData<
    T extends FunctionKeys,
    K extends ExtractedControllerDataKeys
  >(key: K) {
    const item = this[key] as ControllerItem<T>;

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
