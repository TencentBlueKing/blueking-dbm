/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited; a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing; software distributed under the License is distributed
 * on an "AS IS" BASIS; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND; either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import { utcDisplayTime } from '@utils';

import { t } from '@locales/index';

export default class KubernetesOperationLog {
  static CreateCluster = 'CreateCluster';
  static CreateK8sNamespace = 'CreateK8sNamespace';
  static DeleteCluster = 'DeleteCluster';
  static DeleteK8sPod = 'DeleteK8sPod';
  static ExposeService = 'ExposeService';
  static HorizontalScaling = 'HorizontalScaling';
  static PartialUpdateCluster = 'PartialUpdateCluster';
  static RestartCluster = 'RestartCluster';
  static RestartComponent = 'RestartComponent';
  static StartCluster = 'StartCluster';
  static StartComponent = 'StartComponent';
  static StopCluster = 'StopCluster';
  static StopComponent = 'StopComponent';
  static UpdateCluster = 'UpdateCluster';
  static UpgradeComp = 'UpgradeComp';
  static VerticalScaling = 'VerticalScaling';
  static VolumeExpansion = 'VolumeExpansion';

  static RequestTypeMap = {
    [KubernetesOperationLog.CreateCluster]: t('创建集群'),
    [KubernetesOperationLog.CreateK8sNamespace]: t('创建 K8s 命名空间'),
    [KubernetesOperationLog.DeleteCluster]: t('删除集群'),
    [KubernetesOperationLog.DeleteK8sPod]: t('删除 K8s Pod'),
    [KubernetesOperationLog.ExposeService]: t('暴露服务'),
    [KubernetesOperationLog.HorizontalScaling]: t('水平扩缩容'),
    [KubernetesOperationLog.PartialUpdateCluster]: t('局部更新集群'),
    [KubernetesOperationLog.RestartCluster]: t('重启集群'),
    [KubernetesOperationLog.RestartComponent]: t('重启组件'),
    [KubernetesOperationLog.StartCluster]: t('启动集群'),
    [KubernetesOperationLog.StartComponent]: t('启动组件'),
    [KubernetesOperationLog.StopCluster]: t('停止集群'),
    [KubernetesOperationLog.StopComponent]: t('停止组件'),
    [KubernetesOperationLog.UpdateCluster]: t('更新集群'),
    [KubernetesOperationLog.UpgradeComp]: t('升级组件'),
    [KubernetesOperationLog.VerticalScaling]: t('垂直扩缩容'),
    [KubernetesOperationLog.VolumeExpansion]: t('存储扩容'),
  };

  clusterName: string;
  createdAt: string; // ISO 8601 格式时间字符串
  createdBy: string;
  description: string;
  id: number;
  k8sClusterName: string;
  nameSpace: string;
  requestId: string;
  requestParams: string; // JSON 字符串，需要解析后使用
  requestType: string;
  requestTypeAlias: string;
  status: string;
  ticket_status: string;
  ticket_type: string;
  ticket_type_display: string;
  ticketId: number;
  updatedAt: string; // ISO 8601 格式时间字符串
  updatedBy: string;

  constructor(payload = {} as KubernetesOperationLog) {
    this.id = payload.id || 0;
    this.requestId = payload.requestId || '';
    this.k8sClusterName = payload.k8sClusterName || '';
    this.clusterName = payload.clusterName || '';
    this.nameSpace = payload.nameSpace || '';
    this.requestType = payload.requestType || '';
    this.requestTypeAlias = payload.requestTypeAlias || '';
    this.requestParams = payload.requestParams || '';
    this.ticketId = payload.ticketId;
    this.ticket_status = payload.ticket_status;
    this.ticket_type = payload.ticket_type;
    this.ticket_type_display = payload.ticket_type_display;
    this.status = payload.status || '';
    this.description = payload.description || '';
    this.createdBy = payload.createdBy || '';
    this.createdAt = payload.createdAt || '';
    this.updatedBy = payload.updatedBy || '';
    this.updatedAt = payload.updatedAt || '';
  }

  get createdAtDisplay() {
    return utcDisplayTime(this.createdAt);
  }

  get requestParamsFormat() {
    return JSON.parse(this.requestParams);
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.updatedAt);
  }
}
