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
  <TableEditSelect
    ref="editSelectRef"
    :list="list"
    :model-value="modelValue"
    :placeholder="t('请选择')"
    :rules="rules"
    @change="(value) => handleChange(value as string)">
    <template #default="{ optionItem }">
      <div class="role-host-select-option">
        <div>{{ optionItem.label }}</div>
        <div class="option-count">{{ optionItem.count }}</div>
      </div>
    </template>
  </TableEditSelect>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopo } from '@services/source/ipchooser';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  interface Props {
    modelValue: string;
  }

  interface Emits {
    (e: 'change', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('主机来源不能为空'),
    },
  ];

  const editSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref('');
  const list = ref([
    {
      value: 'idle',
      label: t('业务空闲机'),
      count: 0,
    },
  ]);

  const getHostsCount = () => {
    getHostTopo({
      mode: 'idle_only',
      all_scope: true,
      scope_list: [
        {
          scope_id: window.PROJECT_CONFIG.BIZ_ID,
          scope_type: 'biz',
        },
      ],
    }).then((data) => {
      if (data) {
        const [first] = list.value;
        first.count = data[0].count || 0;
      }
    });
  };

  const handleChange = (value: string) => {
    localValue.value = value;
    emits('change', localValue.value);
  };

  watch(
    () => props.modelValue,
    () => {
      localValue.value = props.modelValue;
    },
    {
      immediate: true,
    },
  );

  onMounted(() => {
    getHostsCount();
  });

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value!.getValue().then(() => ({
        host_source: localValue.value,
      }));
    },
  });
</script>

<style lang="less">
  .role-host-select-option {
    display: flex;
    width: 100%;

    .option-count {
      width: 23px;
      height: 16px;
      padding: 0 8px;
      margin-left: auto;
      color: #979ba5;
      background-color: #f0f1f5;
      border-radius: 2px;
    }
  }
</style>
