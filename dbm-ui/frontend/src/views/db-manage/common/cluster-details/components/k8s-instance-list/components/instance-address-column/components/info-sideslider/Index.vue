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
  <BkSideslider
    v-model:is-show="isShow"
    render-directive="if"
    :width="1100">
    <template #header>
      <div class="k8s-instance-column-sideslider-header">
        <span>{{ t('实例详情') }}</span>
        <div class="header-divider ml-8 mr-8" />
        <div>
          <div class="instance-address">{{ data.podName }}</div>
          <div class="info-box mt-4">
            <div class="info-item">
              <span class="info-label">IP：</span>
              <span>{{ data.node }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('组件类型') }}：</span>
              <span>{{ role }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('状态') }}：</span>
              <ClusterInstanceStatus :data="data.status" />
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('资源配置') }}：</span>
              <span>{{ `${data.resourceQuota.limitCpu}C / ${data.resourceQuota.limitMemory}GB` }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
    <div class="k8s-instance-column-sideslider-content">
      <BkTab
        v-model:active="active"
        type="card-grid">
        <BkTabPanel
          v-for="item in panels"
          :key="item.name"
          :label="item.label"
          :name="item.name">
        </BkTabPanel>
        <div class="content-box">
          <Config
            v-if="active === 'config'"
            :cluster-data="clusterData"
            :cluster-type="clusterType"
            :pod-name="data.podName"
            :role="role" />
          <Log
            v-if="active === 'log'"
            :cluster-data="clusterData"
            :pod-name="data.podName"
            :role="role" />
        </div>
      </BkTab>
    </div>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import SurrealdbHaInstanceModel from '@services/model/surrealdb/surrealdb-ha-instance';
  import SurrealdbSingleInstanceModel from '@services/model/surrealdb/surrealdb-single-instance';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import Config from './components/Config.vue';
  import Log from './components/Log.vue';

  interface Props {
    clusterData: {
      cluster_name: string;
      db_type: string;
      k8s_cluster_name: string;
      namespace: string;
    };
    clusterType: ComponentProps<typeof Config>['clusterType'];
    data: SurrealdbHaInstanceModel | SurrealdbSingleInstanceModel;
    role: string;
  }

  defineProps<Props>();
  const isShow = defineModel<boolean>();

  const { t } = useI18n();

  const panels = [
    { label: t('配置信息'), name: 'config' },
    { label: t('运行日志'), name: 'log' },
  ];

  const active = ref('config');
</script>

<style lang="less">
  .k8s-instance-column-sideslider-header {
    display: flex;
    align-items: center;

    .header-divider {
      width: 1px;
      height: 12px;
      background: #dcdee5;
    }

    .instance-address {
      font-size: 14px;
      font-weight: bolder;
      color: #4d4f56;
    }

    .info-box {
      display: flex;
      align-items: center;
      font-size: 12px;
      gap: 16px;

      .info-item {
        display: flex;
        align-items: center;

        .info-label {
          color: #979ba5;
        }
      }
    }
  }

  .k8s-instance-column-sideslider-content {
    height: 100%;

    .bk-tab .bk-tab-header {
      padding: 16px 24px 0 16px;
      line-height: 42px !important;
      background-color: #f5f7fa;
    }

    .content-box {
      padding: 0 24px;
    }
  }
</style>
