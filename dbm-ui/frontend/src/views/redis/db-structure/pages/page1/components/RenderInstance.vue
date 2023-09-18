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
    <TableEditSelect
      v-if="localValue.length < 2"
      ref="selectRef"
      v-model="localValue"
      :list="selectList"
      multiple
      :placeholder="$t('请选择实例')"
      :rules="rules"
      @change="(value) => handleChange(value as string[])" />
    <BkPopover
      v-else
      :content="$t('批量添加')"
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
        <TableEditSelect
          ref="selectRef"
          v-model="localValue"
          :disabled="isTendisplus"
          :list="selectList"
          multiple
          :placeholder="$t('请选择实例')"
          :rules="rules"
          @change="(value) => handleChange(value as string[])" />
        <div
          v-if="localValue.length > 1"
          class="more-box">
          <BkTag>
            +{{ localValue.length - 1 }}
          </BkTag>
        </div>
      </div>
    </BkPopover>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@views/redis/common/edit/Select.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    clusterType: IDataRow['clusterType'];
    data?: IDataRow['instances'];
    isLoading?: boolean;
  }

  interface Emits {
    (e: 'change', value: string[]): void
  }

  interface Exposes {
    getValue: () => Promise<string[]>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const localValue = ref<string[]>([]);
  const selectRef = ref();
  const isTendisplus = computed(() => props.clusterType === 'PredixyTendisplusCluster');

  const selectList = computed(() => {
    if (props.data) {
      return props.data.map(item => ({ value: item, label: item }));
    }
    return [];
  });

  const rules = [
    {
      validator: (arr: string[]) => arr.length > 0,
      message: t('请选择实例'),
    },
  ];

  watch(isTendisplus, (status) => {
    if (status && props.data) {
      localValue.value = props.data;
    }
  }, {
    immediate: true,
  });

  watch(localValue, (chooseList) => {
    if (chooseList.length > 0) {
      emits('change', chooseList);
    }
  }, {
    immediate: true,
  });

  const handleChange = (value: string[]) => {
    localValue.value = value;
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      if (isTendisplus.value && props.data) {
        return Promise.resolve(props.data);
      }
      return selectRef.value.getValue().then(() => (localValue.value));
    },
  });

</script>
<style lang="less" scoped>
  .item-input {
    width: 100%;
    height: 40px;
    border: 1px solid transparent;

    :deep(.bk-select-trigger) {
      height: 100%;
      background: transparent;

      .bk-input {
        position: relative;
        height: 100%;
        overflow: hidden;
        background: transparent;
        border: none;
        outline: none;

        input {
          background: transparent;
        }
      }
    }

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }
  }

  .content {
    position: relative;

    .more-box{
      position: absolute;
      top: 0;
      right: 3px;

      .bk-tag {
        padding: 0 4px;
      }
    }
  }
</style>
