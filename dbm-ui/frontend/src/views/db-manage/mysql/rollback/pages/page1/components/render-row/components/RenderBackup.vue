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
    :list="targetList"
    :model-value="localValue"
    :placeholder="t('请选择')"
    :rules="rules"
    @change="(value) => handleChange(value as BackupSources)" />
</template>

<script lang="ts">
  import { t } from '@locales/index';

  export enum BackupSources {
    REMOTE = 'remote',
    LOCAL = 'local',
  }

  export const backupSourceList = [
    {
      value: BackupSources.REMOTE,
      label: t('远程备份'),
    },
    {
      value: BackupSources.LOCAL,
      label: t('本地备份'),
    },
  ];

  interface Props {
    modelValue: BackupSources;
    list?: {
      value: string;
      label: string;
    }[];
  }

  interface Emits {
    (e: 'change', value: BackupSources): void;
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>;
  }
</script>
<script setup lang="ts">
  import { ref } from 'vue';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('备份源不能为空'),
    },
  ];
  const targetList = props.list || backupSourceList;

  const editSelectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref(BackupSources.REMOTE);

  const handleChange = (value: BackupSources) => {
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

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef
        .value!.getValue()
        .then(() => ({
          backup_source: localValue.value,
        }))
        .catch(() =>
          Promise.reject({
            backup_source: localValue.value,
          }),
        );
    },
  });
</script>
