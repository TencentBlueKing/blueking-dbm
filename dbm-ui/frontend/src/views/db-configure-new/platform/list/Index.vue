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
    <div class="platform-config-content">
      <BkTab
        v-model:active="activeConfType"
        type="card-tab">
        <BkTabPanel
          v-for="tab of confTypeTabs"
          :key="tab.conf_type"
          :label="tab.name"
          :name="tab.conf_type"
          render-directive="if">
          <OperationRecord
            v-if="tab.conf_type === 'operationRecord'"
            :cluster-type="activeClusterType" />
          <ConfigDatabase
            v-else
            :cluster-type="activeClusterType"
            :conf-type="tab.conf_type" />
        </BkTabPanel>
      </BkTab>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getListConfTypes } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import ClusterTab from '@components/cluster-tab/Index.vue';

  import ConfigDatabase from './components/ConfigDatabase.vue';
  import OperationRecord from './components/OperationRecord.vue';

  const { t } = useI18n();

  const activeClusterType = ref<ClusterTypes>(ClusterTypes.TENDBSINGLE);
  const activeConfType = ref('');

  provide('activeClusterType', activeClusterType);

  const confTypeTabs = ref<ServiceReturnType<typeof getListConfTypes>>([]);

  const { run: fetchConfTypeTabs } = useRequest(getListConfTypes, {
    manual: true,
    onSuccess(res) {
      confTypeTabs.value = [
        ...res,
        {
          conf_type: 'operationRecord',
          name: t('操作记录'),
        },
      ];
      if (!activeConfType.value) {
        activeConfType.value = res[0]?.conf_type || '';
      }
    },
  });

  watch(
    activeClusterType,
    (val) => {
      if (val) {
        activeConfType.value = '';
        fetchConfTypeTabs({ meta_cluster_type: val });
      }
    },
    { immediate: true },
  );
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
</style>
