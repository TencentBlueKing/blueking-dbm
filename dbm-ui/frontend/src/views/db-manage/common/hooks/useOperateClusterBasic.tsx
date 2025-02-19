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
            class='ml-8'
            style='color: #313238'>
            {dataList.map((item) => item.cluster_name).join('，')}
          </span>
        </div>
        <div class='mt-4'>{t('被禁用后将无法访问，如需恢复访问，可以再次「启用」')}</div>
      </div>
    );
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('禁用'),
      contentAlign: 'left',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onConfirm: () => {
        handleConfirm(ticketTypeInfo.disable, dataList);
      },
      subTitle,
      theme: 'danger',
      title: t('确定禁用集群？'),
    });
  };

  const handleEnableCluster = <T extends ClusterCommon>(dataList: T[]) => {
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            class='ml-8'
            style='color: #313238'>
            {dataList.map((item) => item.cluster_name).join('，')}
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
        handleConfirm(ticketTypeInfo.enable, dataList);
      },
      subTitle,
      title: t('确定启用集群？'),
    });
  };

  const handleDeleteCluster = <T extends ClusterCommon>(dataList: T[]) => {
    const clusterNames = dataList.map((item) => item.cluster_name).join('，');
    const subTitle = (
      <div style='background-color: #F5F7FA; padding: 8px 16px;'>
        <div>
          {t('集群')} :
          <span
            class='ml-8'
            style='color: #313238'>
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
      cancelText: t('取消'),
      confirmText: t('删除'),
      contentAlign: 'left',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onConfirm: () => {
        handleConfirm(ticketTypeInfo.delete, dataList);
      },
      subTitle,
      theme: 'danger',
      title: t('确定删除集群？'),
    });
  };

  return {
    handleDeleteCluster,
    handleDisableCluster,
    handleEnableCluster,
  };
};
