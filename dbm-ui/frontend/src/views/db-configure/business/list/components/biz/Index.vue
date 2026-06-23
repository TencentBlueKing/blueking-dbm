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
  <div class="biz-content">
    <BkTab
      v-model:active="activeConfType"
      type="card-tab">
      <BkTabPanel
        v-for="tab of confTypeTabs"
        :key="tab.conf_type"
        :label="tab.name"
        :name="tab.conf_type"
        render-directive="if">
        <OperationRecord v-if="tab.conf_type === 'operationRecord'" />
        <ConfigDatabase
          v-else
          :conf-type="tab.conf_type"
          :namespace="tab.namespace" />
      </BkTabPanel>
    </BkTab>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getListConfTypes } from '@services/source/configs';

  import { ClusterTypes } from '@common/const/clusterTypes.ts';

  import { getConfigureState, saveConfigureState } from '@/views/db-configure/utils/configureState.ts';

  import OperationRecord from '../OperationRecord.vue';

  import ConfigDatabase from './components/ConfigDatabase.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const activeClusterType = inject('activeClusterType', ref(ClusterTypes.TENDBSINGLE));

  /** 初始化 activeConfType（优先从 sessionStorage 恢复 tab） */
  const getInitialActiveConfType = (): string => {
    const savedState = getConfigureState();
    return savedState.activeTab || (route.params.tabName as string) || '';
  };
  const activeConfType = ref(getInitialActiveConfType());

  /** 同步 confType 到 URL 并保存 tab 到 sessionStorage */
  watch(
    activeConfType,
    (value) => {
      // 有值时才同步到 URL，避免空值清掉已有的 tabName
      if (value) {
        router.replace({
          params: {
            ...route.params,
            clusterType: activeClusterType.value,
            tabName: value,
          },
        });
        saveConfigureState({ activeTab: value });
      }
    },
    {
      immediate: true,
    },
  );

  const confTypeTabs = ref<ServiceReturnType<typeof getListConfTypes>>([]);

  const { run: fetchConfTypeTabs } = useRequest(getListConfTypes, {
    manual: true,
    onSuccess(res) {
      const base = [
        ...res,
        {
          conf_type: 'operationRecord',
          name: t('配置变更记录'),
          namespace: 'operationRecord',
        },
      ];
      confTypeTabs.value = base;

      // 从 sessionStorage 恢复 activeTab
      const savedState = getConfigureState();
      if (!activeConfType.value && savedState.activeTab) {
        if (base.find((tab) => tab.conf_type === savedState.activeTab)) {
          activeConfType.value = savedState.activeTab;
          return;
        }
      }

      // 如果没有保存的状态，使用默认值
      if (!activeConfType.value && res.length > 0) {
        activeConfType.value = res[0]?.conf_type;
      }
    },
  });

  watch(
    activeClusterType,
    () => {
      fetchConfTypeTabs({ meta_cluster_type: activeClusterType.value });
    },
    { immediate: true },
  );
</script>

<style lang="less" scoped>
  .biz-content {
    background-color: #fff;
    border-radius: 2px;
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

    :deep(.bk-tab-content) {
      padding: 16px 16px 0;
    }
  }
</style>
