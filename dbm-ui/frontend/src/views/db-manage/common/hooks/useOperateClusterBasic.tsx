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

import { createTicket } from '@services/source/ticket';

import { useTicketMessage } from '@hooks';

import { ClusterTypes, TicketTypes } from '@common/const';

interface ClusterCommon {
  cluster_alias: string;
  cluster_name: string;
  cluster_type: string;
  id: number;
  phase: string;
}

export const useOperateClusterBasic = (clusterType: ClusterTypes, options: { onSuccess: () => void }) => {
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
      disable: TicketTypes;
      enable: TicketTypes;
      delete: TicketTypes;
    }
  > = {
    [ClusterTypes.TENDBSINGLE]: {
      disable: TicketTypes.MYSQL_SINGLE_DISABLE,
      enable: TicketTypes.MYSQL_SINGLE_ENABLE,
      delete: TicketTypes.MYSQL_SINGLE_DESTROY,
    },
    [ClusterTypes.TENDBHA]: {
      disable: TicketTypes.MYSQL_HA_DISABLE,
      enable: TicketTypes.MYSQL_HA_ENABLE,
      delete: TicketTypes.MYSQL_HA_DESTROY,
    },
    [ClusterTypes.TENDBCLUSTER]: {
      disable: TicketTypes.TENDBCLUSTER_DISABLE,
      enable: TicketTypes.TENDBCLUSTER_ENABLE,
      delete: TicketTypes.TENDBCLUSTER_DESTROY,
    },
    [ClusterTypes.REDIS]: {
      disable: TicketTypes.REDIS_PROXY_CLOSE,
      enable: TicketTypes.REDIS_PROXY_OPEN,
      delete: TicketTypes.REDIS_DESTROY,
    },
    [ClusterTypes.REDIS_INSTANCE]: {
      disable: TicketTypes.REDIS_INSTANCE_CLOSE,
      enable: TicketTypes.REDIS_INSTANCE_OPEN,
      delete: TicketTypes.REDIS_INSTANCE_DESTROY,
    },
    [ClusterTypes.MONGODB]: {
      disable: TicketTypes.MONGODB_DISABLE,
      enable: TicketTypes.MONGODB_ENABLE,
      delete: TicketTypes.MONGODB_DESTROY,
    },
    [ClusterTypes.SQLSERVER]: {
      disable: TicketTypes.SQLSERVER_DISABLE,
      enable: TicketTypes.SQLSERVER_ENABLE,
      delete: TicketTypes.SQLSERVER_DESTROY,
    },
    [ClusterTypes.DORIS]: {
      disable: TicketTypes.DORIS_DISABLE,
      enable: TicketTypes.DORIS_ENABLE,
      delete: TicketTypes.DORIS_DESTROY,
    },
    [ClusterTypes.ES]: {
      disable: TicketTypes.ES_DISABLE,
      enable: TicketTypes.ES_ENABLE,
      delete: TicketTypes.ES_DESTROY,
    },
    [ClusterTypes.HDFS]: {
      disable: TicketTypes.HDFS_DISABLE,
      enable: TicketTypes.HDFS_ENABLE,
      delete: TicketTypes.HDFS_DESTROY,
    },
    [ClusterTypes.KAFKA]: {
      disable: TicketTypes.KAFKA_DISABLE,
      enable: TicketTypes.KAFKA_ENABLE,
      delete: TicketTypes.KAFKA_DESTROY,
    },
    [ClusterTypes.PULSAR]: {
      disable: TicketTypes.PULSAR_DISABLE,
      enable: TicketTypes.PULSAR_ENABLE,
      delete: TicketTypes.PULSAR_DESTROY,
    },
    [ClusterTypes.RIAK]: {
      disable: TicketTypes.RIAK_CLUSTER_DISABLE,
      enable: TicketTypes.RIAK_CLUSTER_ENABLE,
      delete: TicketTypes.RIAK_CLUSTER_DESTROY,
    },
  };

  const ticketTypeInfo = ticketTypeMap[clusterType];

  const handleConfirm = (ticketType: TicketTypes, dataList: { id: number }[]) => {
    createTicket({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      ticket_type: ticketType,
      details: getDetailParam(ticketType, dataList),
    }).then((data) => {
      options.onSuccess();
      ticketMessage(data.id);
    });
  };

  const handleDisableCluster = <T extends ClusterCommon>(dataList: T[]) => {
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            style='color: #313238'
            class='ml-8'>
            {dataList.map((item) => item.cluster_name).join('，')}
          </span>
        </div>
        <div class='mt-4'>{t('被禁用后将无法访问，如需恢复访问，可以再次「启用」')}</div>
      </div>
    );
    InfoBox({
      title: t('确定禁用集群？'),
      subTitle,
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('禁用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        handleConfirm(ticketTypeInfo.disable, dataList);
      },
    });
  };

  const handleEnableCluster = <T extends ClusterCommon>(dataList: T[]) => {
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            style='color: #313238'
            class='ml-8'>
            {dataList.map((item) => item.cluster_name).join('，')}
          </span>
        </div>
        <div class='mt-4'>{t('启用后，将会恢复访问')}</div>
      </div>
    );
    InfoBox({
      title: t('确定启用集群？'),
      subTitle,
      confirmText: t('启用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        handleConfirm(ticketTypeInfo.enable, dataList);
      },
    });
  };

  const handleDeleteCluster = <T extends ClusterCommon>(dataList: T[]) => {
    const clusterNames = dataList.map((item) => item.cluster_name).join('，');
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            style='color: #313238'
            class='ml-8'>
            {clusterNames}
          </span>
        </div>
        <div class='mt-4'>{t('删除后将产生以下影响')}：</div>
        <div class='mt-4'>1. {t('删除xxx集群', [clusterNames])}</div>
        <div class='mt-4'>2. {t('删除xxx实例数据，停止相关进程', [clusterNames])}</div>
        <div class='mt-4'>3. {t('回收主机')}：</div>
      </div>
    );
    InfoBox({
      title: t('确定删除集群？'),
      subTitle,
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('删除'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        handleConfirm(ticketTypeInfo.delete, dataList);
      },
    });
  };

  return {
    handleDisableCluster,
    handleEnableCluster,
    handleDeleteCluster,
  };
};
