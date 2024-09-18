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
  <span
    v-bk-tooltips="batchIconsInfoMap[type].tooltip"
    class="batch-edit-btn">
    <DbIcon :type="batchIconsInfoMap[type].icon" />
  </span>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    type?: 'edit' | 'select' | 'entry';
  }

  withDefaults(defineProps<Props>(), {
    type: 'select',
  });

  const { t } = useI18n();

  const batchIconsInfoMap = {
    edit: {
      tooltip: t('统一设置：将该列统一设置为相同的值'),
      icon: 'bulk-edit',
    },
    entry: {
      tooltip: t('批量编辑：通过换行分隔，快速批量录入多个值'),
      icon: 'piliangluru',
    },
    select: {
      tooltip: t('批量选择'),
      icon: 'batch-host-select',
    },
  };
</script>
<style lang="less">
  .batch-edit-btn {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
