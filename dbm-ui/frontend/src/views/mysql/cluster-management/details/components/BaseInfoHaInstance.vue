<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <DbCard
    class="base-info"
    :title="$t('基本信息')">
    <EditInfo
      :columns="columns"
      :data="data" />
  </DbCard>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { InstanceDetails } from '@services/types/clusters';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  interface Props {
    data: InstanceDetails
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const columns: InfoColumn[][] = [
    [
      {
        label: t('实例'),
        key: 'instance_address',
      },
      {
        label: t('主机IP'),
        key: 'bk_host_innerip',
      },
      {
        label: t('状态'),
        key: 'status',
        render: () => {
          const status = props.data.status as ClusterInstStatus;
          if (!status) return '--';

          const info = clusterInstStatus[status] || clusterInstStatus.unavailable;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        label: t('主域名'),
        key: 'master_domain',
        render: () => {
          const domain = props.data.master_domain;
          if (!domain) return '--';

          return (
            <div class="inline-item">
              <div class="text-overflow" v-overflow-tips>
                <a href="javascript:" onClick={handleToClusterDetails}>{domain}</a>
              </div>
              <i class="db-icon-link ml-4" />
            </div>
          );
        },
      },
      {
        label: t('从域名'),
        key: 'slave_domain',
      },
      {
        label: t('云区域'),
        key: 'bk_cloud_name',
      },
      {
        label: t('所在城市'),
        key: 'idc_city_name',
      },
      {
        label: t('所在机房'),
        key: 'bk_idc_name',
      },
    ],
    [
      {
        label: t('部署架构'),
        key: 'cluster_type_display',
      },
      {
        label: t('部署角色'),
        key: 'role',
      },
      {
        label: t('部署时间'),
        key: 'create_at',
      },
      {
        label: 'CPU',
        key: 'bk_cpu',
        render: () => {
          if (!Number.isFinite(props.data.bk_cpu)) {
            return '--';
          }
          return `${props.data.bk_cpu}${t('核')}`;
        },
      },
      {
        label: t('内存'),
        key: 'bk_mem',
        render: () => {
          if (!Number.isFinite(props.data.bk_mem)) {
            return '--';
          }
          return `${props.data.bk_mem}MB`;
        },
      },
      {
        label: t('磁盘'),
        key: 'bk_disk',
        render: () => {
          if (!Number.isFinite(props.data.bk_disk)) {
            return '--';
          }
          return `${props.data.bk_disk}GB`;
        },
      },
    ],
  ];

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = () => {
    router.push({
      name: 'DatabaseTendbha',
      query: {
        cluster_id: props.data.cluster_id,
      },
    });
  };
</script>

<style lang="less" scoped>
.base-info {
  box-shadow: unset;

  :deep(.inline-item) {
    display: flex;
    align-items: center;

    .db-icon-link {
      color: @primary-color;
      cursor: pointer;
      flex-shrink: 0;
    }
  }
}
</style>
