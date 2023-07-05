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
    <div
      class="render-spec-box"
      @mouseleave="handleMouseLeave"
      @mouseover="handleMouseOver">
      <TableEditSelect
        ref="selectRef"
        v-model="localValue"
        :list="list"
        :placeholder="$t('输入集群后自动生成')"
        :rules="rules"
        @change="(value) => handleChange(value as string)" />
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { IDataRow } from './Row.vue';
  import TableEditSelect from './SpecSelect.vue';


  interface Props {
    data?: IDataRow['spec'];
    isLoading?: boolean;
  }


  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = defineProps<Props>();
  const isShowEye = ref(true);
  const selectRef = ref();
  const localValue = ref('');

  const { t } = useI18n();

  const list = computed(() => {
    if (props.data) {
      const obj = {
        id: props.data.name,
        name: props.data.name,
        specData: props.data,
      };
      return [obj];
    }
    return [];
  });

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请先输入集群'),
    },
  ];

  const handleChange = (value: string) => {
    localValue.value = value;
  };

  const handleMouseOver = () => {
    if (props.data?.name) isShowEye.value = true;
  };

  const handleMouseLeave = () => {
    isShowEye.value = false;
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value
        .getValue()
        .then(() => (localValue.value));
    },
  });

</script>
<style lang="less" scoped>
.render-spec-box {
  line-height: 20px;
  color: #63656e;
}

.eye {
  font-size: 15px;
  color: #3A84FF;

  &:hover {
    cursor: pointer;
  }
}
</style>
