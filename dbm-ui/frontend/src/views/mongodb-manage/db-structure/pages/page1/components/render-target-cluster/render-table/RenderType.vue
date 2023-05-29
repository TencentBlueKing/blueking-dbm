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
    v-model="localBackupType"
    :list="targetList" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditSelect from '@components/render-table/columns/select/index.vue';

  interface Emits {
    (e: 'structTypeChange', value: string): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const targetList = [
    {
      value: 'REMOTE_AND_BACKUPID',
      label: t('备份记录'),
    },
    {
      value: 'REMOTE_AND_TIME',
      label: t('回档到指定时间'),
    },
  ];

  const localBackupType = ref('REMOTE_AND_BACKUPID');

  watch(
    localBackupType,
    (type) => {
      emits('structTypeChange', type);
    },
    {
      immediate: true,
    },
  );
</script>
