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
  <div class="base-info-list pt-20">
    <ul
      v-for="(list, index) of columns"
      :key="index"
      class="base-info-column">
      <li
        v-for="config of list"
        :key="config.key"
        class="base-info-item">
        <span class="base-info-label">
          <span
            v-overflow-tips
            class="text-overflow">
            {{ config.label }}
          </span>
          ：
        </span>
        <div class="base-info-value-container">
          <span
            v-overflow-tips
            class="base-info-value text-overflow">
            <Component
              :is="config.render"
              v-if="config.render" />
            <template v-else>{{ getInfoValue(config.key) || '--' }}</template>
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="tsx">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import OracleHaInstanceModel from '@services/model/oracle/oracle-ha-instance';

  import { type ClusterInstStatus, clusterInstStatus } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  interface Props {
    data: OracleHaInstanceModel;
  }

  interface InfoColumn {
    key: string;
    label: string;
    render?: () => VNode | string | null;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const columns: InfoColumn[][] = [
    [
      {
        key: 'instance_address',
        label: t('实例'),
      },
      {
        key: 'bk_host_innerip',
        label: t('主机IP'),
      },
      {
        key: 'status',
        label: t('状态'),
        render: () => {
          const status = props.data.status as ClusterInstStatus;
          if (!status) {
            return '--';
          }

          const info = clusterInstStatus[status] || clusterInstStatus.unavailable;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        key: 'master_domain',
        label: t('主访问入口'),
        render: () => {
          const domain = props.data.master_domain;
          if (!domain) {
            return '--';
          }

          return (
            <div class='inline-item'>
              <div
                v-overflow-tips
                class='text-overflow'>
                <bk-button
                  text
                  theme='primary'
                  onClick={handleToClusterDetails}>
                  {domain}
                </bk-button>
              </div>
              <db-icon
                class='ml-4'
                type='link'
              />
            </div>
          );
        },
      },
      {
        key: 'slave_domain',
        label: t('从访问入口'),
      },
      {
        key: 'bk_cloud_name',
        label: t('管控区域'),
      },
      {
        key: 'bk_idc_city_name',
        label: t('地域'),
      },
      {
        key: 'bk_sub_zone',
        label: t('所在园区'),
      },
    ],
    [
      {
        key: 'db_version',
        label: t('版本'),
      },
      {
        key: 'cluster_type_name',
        label: t('部署架构'),
      },
      {
        key: 'role',
        label: t('部署角色'),
      },
      {
        key: 'create_at',
        label: t('部署时间'),
      },
      {
        key: 'bk_cpu',
        label: 'CPU',
        render: () => {
          if (!Number.isFinite(props.data.bk_cpu)) {
            return '--';
          }
          return `${props.data.bk_cpu}${t('核')}`;
        },
      },
      {
        key: 'bk_mem',
        label: t('内存'),
        render: () => {
          if (!Number.isFinite(props.data.bk_mem)) {
            return '--';
          }
          return `${props.data.bk_mem}MB`;
        },
      },
      {
        key: 'bk_disk',
        label: t('磁盘'),
        render: () => {
          if (!Number.isFinite(props.data.bk_disk)) {
            return '--';
          }
          return `${props.data.bk_disk}GB`;
        },
      },
    ],
  ];

  const getInfoValue = (key: string) => (props.data as unknown as Record<string, unknown>)[key];

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = () => {
    router.push({
      name: 'OracleHaClusterList',
      query: {
        cluster_id: props.data.cluster_id,
      },
    });
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .base-info-list {
    display: flex;
    font-size: @font-size-mini;

    .base-info-column {
      flex: 0 1 50%;
      max-width: 50%;
    }

    .base-info-item {
      .flex-center();

      line-height: 32px;
    }

    .base-info-label {
      display: flex;
      min-width: 80px !important;
      padding-left: 10px;
      text-align: right;
      flex-shrink: 0;
      justify-content: flex-end;
    }

    .base-info-value-container {
      .flex-center();

      overflow: hidden;
      color: @title-color;
      flex: 1;
    }

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
