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
  <div class="host-agent-status">
    <DbIcon
      svg
      :type="statusIcon" />
    <span style="margin-left: 4px;">
      {{ statusText }}
    </span>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: number;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const iconMap = {
    0: 'abnormal',
    1: 'normal',
  };
  const textMap = {
    0: t('异常'),
    1: t('正常'),
  };
  const statusIcon = computed(() => iconMap[props.data as keyof typeof iconMap]);
  const statusText = computed(() => textMap[props.data as keyof typeof textMap]);
</script>
<style lang="less">
  .host-agent-status {
    display: flex;
    align-items: center;
  }
</style>
