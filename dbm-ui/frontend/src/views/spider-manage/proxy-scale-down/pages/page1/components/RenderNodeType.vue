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
    <div class="render-switch-box">
      <TableEditSelect
        ref="selectRef"
        v-model="localValue"
        :list="selectList"
        :placeholder="$t('请选择')"
        :rules="rules"
        @change="(value) => handleChange(value as string)" />
    </div>
  </BkLoading>
</template>
<script lang="ts">
  export enum NodeType {
    MASTER = 'spider_master',
    SLAVE = 'spider_slave'
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  interface Props {
    data?: string;
    choosed?: string[];
    isLoading?: boolean;
    counts?: {
      master: number,
      slave: number,
    }
  }

  interface Emits {
    (e: 'change', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<string>
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    choosed: () => ([]),
    counts: () => ({
      master: 0,
      slave: 0,
    }),
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const selectRef = ref();
  const localValue = ref(props.data);

  let selectListRaw = [
    {
      value: NodeType.MASTER,
      label: 'Master',
    },
    {
      value: NodeType.SLAVE,
      label: 'Slave',
    },
  ];
  const selectList = ref<{ value: NodeType, label: string }[]>([]);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择节点类型'),
    },
  ];

  watch(() => props.counts, (counts) => {
    const list = [];
    if (counts.master > 0) {
      list.push(selectListRaw[0]);
    }
    if (counts.slave > 0) {
      list.push(selectListRaw[1]);
    }
    selectListRaw = list;
    selectList.value = list;
    if (list.length > 0) {
      localValue.value = list[0].value;
      emits('change', list[0].value);
    }
  }, {
    immediate: true,
  });

  watch(() => props.choosed, (choosedTypes) => {
    if (choosedTypes.length === 0) {
      selectList.value = selectListRaw;
      return;
    }
    if (choosedTypes.length === 1) {
      if (!choosedTypes.includes(localValue.value)) {
        selectList.value = selectListRaw.filter(item => !choosedTypes.includes(item.value));
      } else {
        selectList.value = selectListRaw;
      }
      return;
    }
    if (choosedTypes.length === 2) {
      if (localValue.value !== '') {
        selectList.value = selectListRaw.filter(item => item.value === localValue.value);
        return;
      }
      if (localValue.value === '') {
        selectList.value = selectListRaw.filter(item => !choosedTypes.includes(item.value));
        return;
      }
    }
  }, {
    immediate: true,
    deep: true,
  });

  const handleChange = (value: string) => {
    localValue.value = value as NodeType;
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value
        .getValue()
        .then(() => ({ reduce_spider_role: localValue.value }));
    },
  });
</script>
<style lang="less" scoped>
  .render-switch-box {
    padding: 0;
    color: #63656e;

    :deep(.bk-input--text) {
      border: none;
      outline: none;
    }
  }
</style>
