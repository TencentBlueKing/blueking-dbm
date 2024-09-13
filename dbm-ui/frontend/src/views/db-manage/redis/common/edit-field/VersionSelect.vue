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
  <BkLoading :loading="loading">
    <div class="render-role-box">
      <TableEditSelect
        ref="selectRef"
        v-model="localValue"
        :list="selectList"
        :placeholder="t('请选择')"
        :rules="rules">
        <template #default="{ optionItem, index }">
          <div class="redis-version-select-option">
            <div
              v-overflow-tips
              class="option-label">
              {{ optionItem.label }}
            </div>
            <div>
              <BkTag
                v-if="data === optionItem.label"
                class="ml-4"
                size="small"
                theme="info">
                {{ t('当前版本') }}
              </BkTag>
              <BkTag
                v-if="index === 0"
                class="ml-4"
                size="small"
                theme="warning">
                {{ t('推荐') }}
              </BkTag>
            </div>
          </div>
        </template>
      </TableEditSelect>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listPackages } from '@services/source/package';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  import { clusterTypeMachineMap } from '@views/db-manage/redis/common/const';

  interface Props {
    data?: string;
    clusterType?: string;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    clusterType: '',
  });

  const { t } = useI18n();

  const selectRef = ref();
  const localValue = ref(props.data);
  const selectList = ref<
    {
      value: string;
      label: string;
    }[]
  >([]);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择Redis版本'),
    },
  ];

  const { loading, run: fetchListPackages } = useRequest(listPackages, {
    manual: true,
    onSuccess(listResult) {
      [localValue.value] = listResult;
      selectList.value = listResult.map((value) => ({
        value,
        label: value,
      }));
    },
  });

  watch(
    () => props.clusterType,
    () => {
      if (props.clusterType) {
        fetchListPackages({
          db_type: 'redis',
          query_key: clusterTypeMachineMap[props.clusterType] ?? 'redis',
        });
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value.getValue().then(() => localValue.value);
    },
  });
</script>

<style lang="less">
  .redis-version-select-option {
    display: flex;
    width: 100%;

    .option-label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
<style lang="less" scoped>
  .render-role-box {
    padding: 0;
    color: #63656e;

    :deep(.bk-input--text) {
      border: none;
      outline: none;
    }
  }
</style>
