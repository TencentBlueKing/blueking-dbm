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
        :disabled="!data"
        :list="specList"
        :placeholder="t('请选择规格')"
        :rules="rules"
        @change="(value) => handleChange(value as number)" />
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { SpecInfo } from './components/Panel.vue';
  import TableEditSelect, { type IListItem } from './components/Select.vue';

  interface Props {
    selectList: IListItem[];
    data?: SpecInfo;
    isLoading?: boolean;
  }

  interface Exposes {
    getValue: () => Promise<number>;
  }

  const props = defineProps<Props>();
  const selectRef = ref();
  const localValue = ref();

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('不能为空'),
    },
  ];

  const specList = computed(() =>
    props.selectList.map((item) => ({
      ...item,
      isCurrentSpec: item.specData.id === props.data?.id,
    })),
  );

  watch(
    () => props.data,
    (data) => {
      if (data) {
        localValue.value = data.id;
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
      return selectRef.value.getValue().then(() => Number(localValue.value));
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
    color: #3a84ff;

    &:hover {
      cursor: pointer;
    }
  }
</style>
