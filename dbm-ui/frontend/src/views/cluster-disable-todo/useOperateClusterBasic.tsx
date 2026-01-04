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

import { InfoBox } from 'bkui-vue';
import { useI18n } from 'vue-i18n';

import TicketClusterDisableTodoModel from '@services/model/ticket-cluster-disable-todo/TicketClusterDisableTodo';
import { createTicket } from '@services/source/ticket';

import { useTicketMessage } from '@hooks';

import { ClusterTypes, TicketTypes } from '@common/const';

export const useOperateClusterBasic = (options: { onSuccess: () => void }) => {
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

  const getDetailParam = (ticketType: TicketTypes, dataList: TicketClusterDisableTodoModel[]) => {
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
      enable: TicketTypes;
    }
  > = {
    [ClusterTypes.DORIS]: {
      delete: TicketTypes.DORIS_DESTROY,
      enable: TicketTypes.DORIS_ENABLE,
    },
    [ClusterTypes.ES]: {
      delete: TicketTypes.ES_DESTROY,
      enable: TicketTypes.ES_ENABLE,
    },
    [ClusterTypes.HDFS]: {
      delete: TicketTypes.HDFS_DESTROY,
      enable: TicketTypes.HDFS_ENABLE,
    },
    [ClusterTypes.KAFKA]: {
      delete: TicketTypes.KAFKA_DESTROY,
      enable: TicketTypes.KAFKA_ENABLE,
    },
    [ClusterTypes.MONGO_REPLICA_SET]: {
      delete: TicketTypes.MONGODB_DESTROY,
      enable: TicketTypes.MONGODB_ENABLE,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      delete: TicketTypes.MONGODB_DESTROY,
      enable: TicketTypes.MONGODB_ENABLE,
    },
    [ClusterTypes.PULSAR]: {
      delete: TicketTypes.PULSAR_DESTROY,
      enable: TicketTypes.PULSAR_ENABLE,
    },
    [ClusterTypes.REDIS]: {
      delete: TicketTypes.REDIS_DESTROY,
      enable: TicketTypes.REDIS_PROXY_OPEN,
    },
    [ClusterTypes.REDIS_INSTANCE]: {
      delete: TicketTypes.REDIS_INSTANCE_DESTROY,
      enable: TicketTypes.REDIS_INSTANCE_OPEN,
    },
    [ClusterTypes.RIAK]: {
      delete: TicketTypes.RIAK_CLUSTER_DESTROY,
      enable: TicketTypes.RIAK_CLUSTER_ENABLE,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      delete: TicketTypes.SQLSERVER_DESTROY,
      enable: TicketTypes.SQLSERVER_ENABLE,
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      delete: TicketTypes.SQLSERVER_DESTROY,
      enable: TicketTypes.SQLSERVER_ENABLE,
    },
    [ClusterTypes.TENDBCLUSTER]: {
      delete: TicketTypes.TENDBCLUSTER_DESTROY,
      enable: TicketTypes.TENDBCLUSTER_ENABLE,
    },
    [ClusterTypes.TENDBHA]: {
      delete: TicketTypes.MYSQL_HA_DESTROY,
      enable: TicketTypes.MYSQL_HA_ENABLE,
    },
    [ClusterTypes.TENDBSINGLE]: {
      delete: TicketTypes.MYSQL_SINGLE_DESTROY,
      enable: TicketTypes.MYSQL_SINGLE_ENABLE,
    },
  };

  const getRealClusterType = (clusterType: ClusterTypes) => {
    if (
      [
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ].includes(clusterType)
    ) {
      return ClusterTypes.REDIS;
    }
    return clusterType;
  };

  const handleConfirm = (ticketType: TicketTypes, dataList: TicketClusterDisableTodoModel[]) => {
    createTicket({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      details: getDetailParam(ticketType, dataList),
      ticket_type: ticketType,
    }).then((data) => {
      options.onSuccess();
      ticketMessage(data.id);
    });
  };

  const handleEnableCluster = (clusterType: ClusterTypes, dataList: TicketClusterDisableTodoModel[]) => {
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            class='ml-8'
            style='color: #313238'>
            {dataList.map((item) => item.immute_domain).join('，')}
          </span>
        </div>
        <div class='mt-4'>{t('启用后，将会恢复访问')}</div>
      </div>
    );
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('启用'),
      contentAlign: 'left',
      footerAlign: 'center',
      headerAlign: 'center',
      onConfirm: () => {
        handleConfirm(ticketTypeMap[getRealClusterType(clusterType)].enable, dataList);
      },
      subTitle,
      title: t('确定启用集群？'),
    });
  };

  const handleDeleteCluster = (clusterType: ClusterTypes, dataList: TicketClusterDisableTodoModel[]) => {
    const domains = dataList.map((item) => item.immute_domain).join('，');
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            class='ml-8'
            style='color: #313238'>
            {domains}
          </span>
        </div>
        <div class='mt-4'>{t('删除后将产生以下影响')}：</div>
        <div class='mt-4'>1. {t('删除xxx集群', [domains])}</div>
        <div class='mt-4'>2. {t('删除xxx实例数据，停止相关进程', [domains])}</div>
        <div class='mt-4'>3. {t('回收主机')}</div>
      </div>
    );
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('删除'),
      contentAlign: 'left',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onConfirm: () => {
        handleConfirm(ticketTypeMap[getRealClusterType(clusterType)].delete, dataList);
      },
      subTitle,
      theme: 'danger',
      title: t('确定删除集群？'),
    });
  };

  return {
    handleDeleteCluster,
    handleEnableCluster,
  };
};
