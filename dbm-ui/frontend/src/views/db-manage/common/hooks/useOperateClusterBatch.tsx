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

import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { createTicket } from '@services/source/ticket';

import { useTicketMessage } from '@hooks';

import { ClusterTypes, TicketTypes } from '@common/const';

import { countBatchOperation } from '@utils';

interface ClusterCommon {
  cluster_alias: string;
  cluster_name: string;
  cluster_type: string;
  id: number;
  phase: string;
}

interface OperateClusterBatchOptions<T = ClusterCommon> {
  /** 删除时状态不符判断（未禁用计入跳过 b） */
  deleteMismatch?: (item: T) => boolean;
  /** 删除操作是否有权限（无权限计入跳过 a） */
  deletePermission?: (item: T) => boolean;
  /** 禁用时状态不符判断（已禁用计入跳过 b） */
  disableMismatch?: (item: T) => boolean;
  /** 禁用操作是否有权限（无权限计入跳过 a） */
  disablePermission?: (item: T) => boolean;
  /** 启用时状态不符判断（已启用计入跳过 b） */
  enableMismatch?: (item: T) => boolean;
  /** 启用操作是否有权限（无权限计入跳过 a） */
  enablePermission?: (item: T) => boolean;
  /** 是否有操作权限，默认全部有权限（无权限计入跳过 a） */
  hasPermission?: (item: T) => boolean;
  onSuccess: () => void;
}

/** 批量操作确认弹窗的数据，供调用方在模板中直接绑定 OperateClusterConfirmDialog */
export interface OperateDialogState<T> {
  /** 操作动作词，如“禁用”“启用”“删除” */
  actionWord: string;
  /** 确认按钮主题 */
  confirmButtonTheme: 'danger' | 'primary';
  /** 确认按钮文案 */
  confirmText: string;
  count: ReturnType<typeof countBatchOperation>;
  /** 明细标题，如“将禁用的集群（{K}）” */
  detailTitle: string;
  /** 状态不符原因词，如“已禁用”“未禁用” */
  reasonWord: string;
  /** 操作提示文案 */
  tip?: string;
  /** 弹窗标题 */
  title: string;
  toOperate: T[];
}

export const useOperateClusterBatch = <T extends ClusterCommon>(
  clusterType: ClusterTypes,
  options: OperateClusterBatchOptions<T>,
) => {
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  // 除 大数据 和 redis集群 暂未支持，其余都已支持批量提单
  const batchOperateTicketTypeList: string[] = [
    TicketTypes.MYSQL_SINGLE_DISABLE,
    TicketTypes.MYSQL_SINGLE_ENABLE,
    TicketTypes.MYSQL_SINGLE_DESTROY,
    TicketTypes.MYSQL_HA_DISABLE,
    TicketTypes.MYSQL_HA_ENABLE,
    TicketTypes.MYSQL_HA_DESTROY,
    TicketTypes.TENDBCLUSTER_DISABLE,
    TicketTypes.TENDBCLUSTER_ENABLE,
    TicketTypes.TENDBCLUSTER_DESTROY,
    TicketTypes.REDIS_INSTANCE_OPEN,
    TicketTypes.REDIS_INSTANCE_CLOSE,
    TicketTypes.REDIS_INSTANCE_DESTROY,
    TicketTypes.MONGODB_DISABLE,
    TicketTypes.MONGODB_ENABLE,
    TicketTypes.MONGODB_DESTROY,
    TicketTypes.SQLSERVER_DISABLE,
    TicketTypes.SQLSERVER_ENABLE,
    TicketTypes.SQLSERVER_DESTROY,
  ];

  const getDetailParam = (ticketType: TicketTypes, dataList: { id: number }[]) => {
    const idList = dataList.map((item) => item.id);
    if (batchOperateTicketTypeList.includes(ticketType as string)) {
      return {
        cluster_ids: idList,
      };
    }
    return {
      cluster_id: idList[0],
    };
  };

  const ticketTypeMap: Record<
    string,
    {
      delete: TicketTypes;
      disable: TicketTypes;
      enable: TicketTypes;
    }
  > = {
    [ClusterTypes.DORIS]: {
      delete: TicketTypes.DORIS_DESTROY,
      disable: TicketTypes.DORIS_DISABLE,
      enable: TicketTypes.DORIS_ENABLE,
    },
    [ClusterTypes.ES]: {
      delete: TicketTypes.ES_DESTROY,
      disable: TicketTypes.ES_DISABLE,
      enable: TicketTypes.ES_ENABLE,
    },
    [ClusterTypes.HDFS]: {
      delete: TicketTypes.HDFS_DESTROY,
      disable: TicketTypes.HDFS_DISABLE,
      enable: TicketTypes.HDFS_ENABLE,
    },
    [ClusterTypes.KAFKA]: {
      delete: TicketTypes.KAFKA_DESTROY,
      disable: TicketTypes.KAFKA_DISABLE,
      enable: TicketTypes.KAFKA_ENABLE,
    },
    [ClusterTypes.MONGODB]: {
      delete: TicketTypes.MONGODB_DESTROY,
      disable: TicketTypes.MONGODB_DISABLE,
      enable: TicketTypes.MONGODB_ENABLE,
    },
    [ClusterTypes.PULSAR]: {
      delete: TicketTypes.PULSAR_DESTROY,
      disable: TicketTypes.PULSAR_DISABLE,
      enable: TicketTypes.PULSAR_ENABLE,
    },
    [ClusterTypes.REDIS]: {
      delete: TicketTypes.REDIS_DESTROY,
      disable: TicketTypes.REDIS_PROXY_CLOSE,
      enable: TicketTypes.REDIS_PROXY_OPEN,
    },
    [ClusterTypes.REDIS_INSTANCE]: {
      delete: TicketTypes.REDIS_INSTANCE_DESTROY,
      disable: TicketTypes.REDIS_INSTANCE_CLOSE,
      enable: TicketTypes.REDIS_INSTANCE_OPEN,
    },
    [ClusterTypes.RIAK]: {
      delete: TicketTypes.RIAK_CLUSTER_DESTROY,
      disable: TicketTypes.RIAK_CLUSTER_DISABLE,
      enable: TicketTypes.RIAK_CLUSTER_ENABLE,
    },
    [ClusterTypes.SQLSERVER]: {
      delete: TicketTypes.SQLSERVER_DESTROY,
      disable: TicketTypes.SQLSERVER_DISABLE,
      enable: TicketTypes.SQLSERVER_ENABLE,
    },
    [ClusterTypes.TENDBCLUSTER]: {
      delete: TicketTypes.TENDBCLUSTER_DESTROY,
      disable: TicketTypes.TENDBCLUSTER_DISABLE,
      enable: TicketTypes.TENDBCLUSTER_ENABLE,
    },
    [ClusterTypes.TENDBHA]: {
      delete: TicketTypes.MYSQL_HA_DESTROY,
      disable: TicketTypes.MYSQL_HA_DISABLE,
      enable: TicketTypes.MYSQL_HA_ENABLE,
    },
    [ClusterTypes.TENDBSINGLE]: {
      delete: TicketTypes.MYSQL_SINGLE_DESTROY,
      disable: TicketTypes.MYSQL_SINGLE_DISABLE,
      enable: TicketTypes.MYSQL_SINGLE_ENABLE,
    },
  };

  const ticketTypeInfo = ticketTypeMap[clusterType];

  const handleConfirm = (ticketType: TicketTypes, dataList: { id: number }[]) => {
    createTicket({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details: getDetailParam(ticketType, dataList),
      ticket_type: ticketType,
    }).then((data) => {
      isShow.value = false;
      options.onSuccess();
      ticketMessage(data.id);
    });
  };

  /** 计算批量操作计数与将提交列表（一行只算一次，无权限优先） */
  const getOperateInfo = (dataList: T[], permission: (item: T) => boolean, mismatched?: (item: T) => boolean) => {
    const hasPermission = permission;
    const isMismatch = mismatched ?? (() => false);
    const count = countBatchOperation(dataList, {
      hasPermission,
      statusMismatch: isMismatch,
    });
    const toOperate = dataList.filter((item) => hasPermission(item) && !isMismatch(item));
    return { count, toOperate };
  };

  /** 批量操作确认弹窗是否显示 */
  const isShow = ref(false);

  /** 批量操作确认弹窗的数据 */
  const operateDialog = ref<OperateDialogState<T>>({
    actionWord: '',
    confirmButtonTheme: 'primary',
    confirmText: '',
    count: { a: 0, b: 0, k: 0, n: 0, s: 0 },
    detailTitle: '',
    reasonWord: '',
    tip: '',
    title: '',
    toOperate: [],
  });

  /** 当前待提交的单据类型 */
  const currentTicketType = ref<TicketTypes>(TicketTypes.MYSQL_SINGLE_DISABLE);

  /** 弹窗确认回调 */
  const handleConfirmDialog = () => {
    handleConfirm(currentTicketType.value, operateDialog.value.toOperate);
  };

  /** 打开弹窗并填充数据 */
  const openDialog = (
    ticketType: TicketTypes,
    opts: Pick<
      OperateDialogState<T>,
      | 'actionWord'
      | 'confirmButtonTheme'
      | 'confirmText'
      | 'count'
      | 'detailTitle'
      | 'reasonWord'
      | 'tip'
      | 'title'
      | 'toOperate'
    >,
  ) => {
    currentTicketType.value = ticketType;
    operateDialog.value = { ...opts };
    isShow.value = true;
  };

  const handleDisableCluster = (dataList: T[]) => {
    const { count, toOperate } = getOperateInfo(
      dataList,
      options.disablePermission ?? options.hasPermission ?? (() => true),
      options.disableMismatch,
    );
    openDialog(ticketTypeInfo.disable, {
      actionWord: t('禁用'),
      confirmButtonTheme: 'primary',
      confirmText: t('禁用'),
      count,
      detailTitle: t('将禁用的集群（{K}）', { K: count.k }),
      reasonWord: t('已禁用'),
      tip: t('已禁用的集群将跳过。禁用后将无法访问，如需恢复，再次启用即可。'),
      title: t('确定批量禁用 {K} 个集群？', { K: count.k }),
      toOperate,
    });
  };

  const handleEnableCluster = (dataList: T[]) => {
    const { count, toOperate } = getOperateInfo(
      dataList,
      options.enablePermission ?? options.hasPermission ?? (() => true),
      options.enableMismatch,
    );
    openDialog(ticketTypeInfo.enable, {
      actionWord: t('启用'),
      confirmButtonTheme: 'primary',
      confirmText: t('启用'),
      count,
      detailTitle: t('将启用的集群（{K}）', { K: count.k }),
      reasonWord: t('已启用'),
      tip: t('已启用的集群将跳过。启用后将恢复访问。'),
      title: t('确定批量启用 {K} 个集群？', { K: count.k }),
      toOperate,
    });
  };

  const handleDeleteCluster = (dataList: T[]) => {
    const { count, toOperate } = getOperateInfo(
      dataList,
      options.deletePermission ?? options.hasPermission ?? (() => true),
      options.deleteMismatch,
    );
    openDialog(ticketTypeInfo.delete, {
      actionWord: t('删除'),
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      count,
      detailTitle: t('将删除的集群（{K}）', { K: count.k }),
      reasonWord: t('未禁用'),
      tip: t('仅已禁用的集群可删除，未禁用的集群将跳过。删除后不可恢复。'),
      title: t('确定批量删除 {K} 个集群？', { K: count.k }),
      toOperate,
    });
  };

  return {
    handleConfirmDialog,
    handleDeleteCluster,
    handleDisableCluster,
    handleEnableCluster,
    isShow,
    operateDialog,
  };
};
