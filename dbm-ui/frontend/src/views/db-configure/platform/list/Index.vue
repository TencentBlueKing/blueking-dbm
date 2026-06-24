<!--
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
-->

<template>
  <div class="platform-config-list">
    <ClusterTab
      v-model="activeClusterType"
      :excludes="[ClusterTypes.ORACLE_SINGLE_NONE, ClusterTypes.ORACLE_PRIMARY_STANDBY]" />
    <ApplyPermissionCatch :key="activeClusterType">
      <div class="platform-config-content">
        <BkTab
          v-if="activeClusterType"
          v-model:active="activeConfType"
          class="platform-config-tab"
          type="card-tab">
          <BkTabPanel
            v-for="tab of confTypeTabs"
            :key="tab.conf_type"
            :label="tab.name"
            :name="tab.conf_type"
            render-directive="if">
            <OperationRecord
              v-if="tab.conf_type === 'operationRecord'"
              :namespace="namespace" />
            <ConfigDatabase
              v-else
              :conf-type="tab.conf_type"
              :namespace="tab.namespace" />
          </BkTabPanel>
        </BkTab>
      </div>
    </ApplyPermissionCatch>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getListConfTypes } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import ClusterTab from '@components/cluster-tab/Index.vue';

  import ConfigDatabase from './components/ConfigDatabase.vue';
  import OperationRecord from './components/OperationRecord.vue';

  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const activeClusterType = ref<ClusterTypes>((route.params.clusterType as ClusterTypes) || ClusterTypes.TENDBSINGLE);
  const activeConfType = ref<string>((route.params.confType as string) || 'dbconf');

  const confTypeTabs = ref<ServiceReturnType<typeof getListConfTypes>>([]);
  const namespace = ref('');

  const { run: fetchConfTypeTabs } = useRequest(getListConfTypes, {
    manual: true,
    onSuccess(res) {
      namespace.value = _.uniq(res.map((item) => item.namespace)).join(',');
      confTypeTabs.value = [
        ...res,
        {
          conf_type: 'operationRecord',
          name: t('配置变更记录'),
          namespace: 'operationRecord',
        },
      ];
      if (!activeConfType.value) {
        activeConfType.value = res[0]?.conf_type || '';
      }
    },
  });

  watch(
    activeClusterType,
    (value, oldValue) => {
      if (value) {
        router.replace({
          params: {
            clusterType: value,
          },
        });

        // 用户切换集群类型时重置配置类型
        if (oldValue) {
          activeConfType.value = '';
        }

        // 先清空旧 tab 数据，避免切换期间展示错误类型的 tabs
        confTypeTabs.value = [];
        fetchConfTypeTabs({ meta_cluster_type: value });
      }
    },
    { immediate: true },
  );

  watch(activeConfType, (value) => {
    if (value) {
      router.replace({
        params: {
          clusterType: activeClusterType.value,
          confType: value,
        },
      });
    }
  });
</script>

<style lang="less" scoped>
  .platform-config-list {
    display: flex;
    height: calc(100vh - var(--notice-height) - 105px);
    flex-direction: column;
  }

  .platform-config-content {
    flex: 1;
    padding: 20px 24px;

    :deep(.bk-tab-content) {
      background: #fff;
      padding-bottom: 0;
    }
  }

  .platform-config-tab {
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);
    border-radius: 2px;
  }
</style>
