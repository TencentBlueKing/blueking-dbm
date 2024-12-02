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
        collapse-tags
        :disabled="!clusterId"
        :list="selectList"
        multiple
        multiple-mode="tag"
        :placeholder="t('请选择')"
        :rules="rules">
        <template #default="{ optionItem }">
          <div class="redis-version-select-option">
            <div
              v-overflow-tips
              class="option-label">
              {{ optionItem.label }}
            </div>
            <div>
              <BkTag
                v-if="optionItem.disabled"
                class="ml-4"
                size="small"
                theme="success">
                {{ t('已安装') }}
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

  import { getRedisClusterModuleInfo } from '@services/source/redisToolbox';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  interface Props {
    data?: string[];
    clusterId: number;
    version: string;
  }

  interface Exposes {
    getValue: () => Promise<string[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
  });

  const { t } = useI18n();

  const selectRef = ref();
  const localValue = ref<string[]>([]);
  const selectList = ref<
    {
      disabled: boolean;
      value: string;
      label: string;
    }[]
  >([]);

  const rules = [
    {
      validator: (value: string[]) => Boolean(value.length),
      message: t('请选择Module'),
    },
  ];

  const { loading, run: fetchClusterModule } = useRequest(getRedisClusterModuleInfo, {
    manual: true,
    onSuccess({ results }) {
      selectList.value = Object.entries(results).map(([key, value]) => ({
        disabled: value,
        value: key,
        label: key,
      }));
    },
  });

  watch(
    () => [props.clusterId, props.version],
    () => {
      if (props.clusterId) {
        fetchClusterModule({
          cluster_id: props.clusterId,
          version: props.version,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.data,
    () => {
      localValue.value = props.data;
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

    :deep(.bk-select-trigger) {
      height: 100% !important;

      .bk-select-tag {
        height: inherit;
        border: none;
      }
    }

    :deep(.is-error) {
      .bk-select-tag {
        background-color: #fff0f1;
      }
    }
  }
</style>
