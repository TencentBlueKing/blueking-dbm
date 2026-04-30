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
          :conf-type-name="tab.name" />
      </BkTabPanel>
    </BkTab>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getListConfTypes } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import ConfigDatabase from './components/ConfigDatabase.vue';
  import OperationRecord from './components/OperationRecord.vue';

  const props = defineProps<{
    clusterType?: ClusterTypes;
  }>();

  const route = useRoute();
  const { t } = useI18n();

  const activeConfType = ref((route.params.confType as string) || '');

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
        activeConfType.value = res[0]?.conf_type;
      }
    },
  });

  watch(
    () => props.clusterType,
    () => {
      if (props.clusterType) {
        fetchConfTypeTabs({ meta_cluster_type: props.clusterType });
      }
    },
    { immediate: true },
  );
</script>

<style lang="less" scoped>
  .biz-content {
    border-radius: 2px;

    :deep(.bk-tab-content) {
      padding-bottom: 0;
    }
  }
</style>
