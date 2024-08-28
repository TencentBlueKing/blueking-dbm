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
  <BkLoading :loading="isLoading">
    <div class="render-spec-box">
      <TableEditSelect
        ref="selectRef"
        v-model="localValue"
        :disabled="!localValue"
        :list="selectList"
        :placeholder="t('输入集群后自动生成')"
        :rules="rules"
        @change="(value) => handleChange(value as number)" />
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  // import type { SpecInfo } from './components/Panel.vue';
  import TableEditSelect, { type IListItem } from './components/Select.vue';

  interface Props {
    cloudId?: number;
    clusterType?: string;
    data?: number;
    currentSpecIds?: number[];
  }

  interface Exposes {
    getValue: () => Promise<{
      spec_id: number;
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    cloudId: 0,
    clusterType: '',
    data: undefined,
    currentSpecIds: () => [],
  });

  const selectRef = ref();
  const localValue = ref();
  const isLoading = ref(false);

  const specList = shallowRef<IListItem[]>([]);

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请先输入集群'),
    },
  ];

  const selectList = computed(() =>
    specList.value.map((item) => Object.assign({}, item, { isCurrent: props.currentSpecIds.includes(item.id) })),
  );

  watch(
    () => props.data,
    async (id) => {
      if (id !== undefined) {
        localValue.value = id;
        if (props.clusterType) {
          isLoading.value = true;
          try {
            const listResult = await getResourceSpecList({
              spec_cluster_type: props.clusterType,
              spec_machine_type: 'spider',
              limit: -1,
              offset: 0,
            });
            const specResultList = listResult.results;
            const countResult = await getSpecResourceCount({
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: props.cloudId,
              spec_ids: specResultList.map((item) => item.spec_id),
            });
            specList.value = specResultList.map((item) => ({
              id: item.spec_id,
              name: item.spec_name,
              isCurrent: false,
              specData: {
                name: item.spec_name,
                cpu: item.cpu,
                id: item.spec_id,
                mem: item.mem,
                count: countResult[item.spec_id],
                storage_spec: item.storage_spec,
              },
            }));
          } finally {
            isLoading.value = false;
          }
        }
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: number) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value.getValue().then(() => ({ spec_id: localValue.value }));
    },
  });
</script>
<style lang="less" scoped>
  .render-spec-box {
    line-height: 20px;
    color: #63656e;
  }

  .default-display {
    background: #fafbfd;
  }
</style>
