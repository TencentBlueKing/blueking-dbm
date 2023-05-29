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
  <TableEditDateTime
    ref="localRollbackTimeRef"
    v-model="localRollbackTime"
    :disabled-date="disableDate"
    ext-popover-cls="not-seconds-date-picker"
    :rules="timerRules"
    type="datetime" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useTimeZoneFormat } from '@hooks';

  import TableEditDateTime from '@views/mysql/common/edit/DateTime.vue';

  interface Exposes {
    getValue: () => Promise<{ rollback_time: string }>
  }

  const disableDate = (date: Date) => date && date.valueOf() > Date.now();

  const { t } = useI18n();
  const formatDateToUTC = useTimeZoneFormat();

  const timerRules = [
    {
      validator: (value: string) => !!value,
      message: t('回档时间不能为空'),
    },
  ];

  const localRollbackTimeRef = ref();
  const localRollbackTime = ref('');

  defineExpose<Exposes>({
    getValue() {
      return localRollbackTimeRef.value.getValue()
        .then(() => ({
          rollback_time: formatDateToUTC(localRollbackTime.value),
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-mode {
    display: flex;

    .action-item {
      flex: 0 0 50%;
      overflow: hidden;
    }
  }

  .local-backup-select {
    position: relative;

    :deep(.table-edit-select) {
      .select-result-text {
        padding-left: 14px;
      }

      .select-placeholder {
        left: 30px;
      }
    }

    .file-flag {
      position: absolute;
      top: 14px;
      left: 8px;
      z-index: 1;
      font-size: 16px;
      color: #c4c6cc;
    }
  }
</style>
