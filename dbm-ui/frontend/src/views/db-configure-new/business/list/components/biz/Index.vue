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
  import { useRoute, useRouter } from 'vue-router';

  import { getListConfTypes } from '@services/source/configs';

  import { ClusterTypes } from '@common/const';

  import OperationRecord from '../OperationRecord.vue';

  import ConfigDatabase from './components/ConfigDatabase.vue';

  const props = defineProps<{
    clusterType?: ClusterTypes;
  }>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const activeConfType = ref((route.query.confType as string) || (route.params.confType as string) || '');

  /** 同步 confType 到 URL */
  watch(activeConfType, (value) => {
    router.replace({
      query: {
        ...route.query,
        confType: value || undefined,
      },
    });
  });

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
    box-shadow: 0 2px 4px 0 rgba(25, 25, 41, 0.05);

    :deep(.bk-tab-content) {
      padding-bottom: 0;
    }
  }
</style>
