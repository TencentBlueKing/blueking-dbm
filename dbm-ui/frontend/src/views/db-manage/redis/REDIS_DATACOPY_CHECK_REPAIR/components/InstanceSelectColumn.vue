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
  <EditableColumn
    field="src_instances"
    :label="t('源实例')"
    :min-width="200">
    <BkPopover
      :disabled="isSelectAll || localValue.length < 2"
      placement="top"
      theme="dark">
      <template #content>
        <div
          v-for="item in localValue"
          :key="item">
          {{ item }}
        </div>
      </template>
      <div class="content">
        <EditableSelect
          v-model="localValue"
          filterable
          :input-search="false"
          multiple
          show-select-all>
          <template #trigger>
            <div class="item-input">
              {{ displayText }}
            </div>
          </template>
          <BkOption
            v-for="item in selectList"
            :key="item"
            :label="item"
            :value="item" />
        </EditableSelect>
        <div
          v-if="!isSelectAll && localValue.length > 1"
          class="more-box">
          <BkTag> +{{ localValue.length - 1 }} </BkTag>
        </div>
      </div>
    </BkPopover>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getRedisList } from '@services/source/redis';

  interface Props {
    srcCluster: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const TotalText = t('全部');

  const localValue = ref<string[]>([]);

  const selectList = shallowRef<string[]>([]);

  const isSelectAll = computed(() => localValue.value.length === selectList.value.length);

  const displayText = computed(() => {
    if (isSelectAll.value) {
      return TotalText;
    }
    const list = localValue.value;
    if (localValue.value.length > 1 && localValue.value[0] === TotalText) {
      list.shift();
    }
    return list.join(' , ');
  });

  watch(
    () => props.srcCluster,
    () => {
      if (props.srcCluster) {
        const [cluster] = props.srcCluster.split(':');
        getRedisList({ domain: cluster }).then((result) => {
          if (result.results.length > 0) {
            selectList.value = result.results[0].redis_master.map((row) => `${row.ip}:${row.port}`);
            if (localValue.value.length === 0) {
              localValue.value = selectList.value;
            }
          }
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    isSelectAll,
    () => {
      modelValue.value = isSelectAll.value ? ['all'] : localValue.value;
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .item-input {
    width: 100%;
    padding: 0 16px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;

    :deep(.bk-input) {
      position: relative;
      overflow: hidden;
      border: none;
    }
  }

  .content {
    position: relative;
    width: 100%;

    .more-box {
      position: absolute;
      top: 0;
      right: 3px;

      .bk-tag {
        padding: 0 4px;
      }
    }
  }
</style>
