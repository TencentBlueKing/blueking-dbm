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
    <BkSelect
      v-model="localValue"
      class="item-input"
      filterable
      :input-search="false"
      multiple
      show-select-all>
      <BkOption
        v-for="item in selectList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </BkSelect>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['instances'];
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<string[]>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const localValue = ref<string[]>([]);

  const selectList = computed(() => (props.data ? props.data.map(item => ({ value: item, label: item })) : []));

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve(localValue.value);
    },
  });
</script>
<style lang="less" scoped>


  .item-input {
    width: 100%;
    height: 40px;

    :deep(.bk-input) {
      position: relative;
      height: 40px;
      overflow: hidden;
      border: none;
    }
  }
</style>
