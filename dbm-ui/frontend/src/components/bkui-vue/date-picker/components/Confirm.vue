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
  <div class="dbm-date-picker-confirm">
    <span
      v-if="showTime"
      class="dbm-date-picker-confirm-time"
      :class="{ 'is-disabled': timeDisabled }"
      @click="handleToggleTime">
      {{ isTime ? t('选择日期') : t('选择时间') }}
    </span>
    <span
      v-if="clearable"
      class="dbm-date-picker-confirm-btn"
      @click="emits('clear')">
      {{ t('清空') }}
    </span>
    <span
      class="dbm-date-picker-confirm-btn is-primary"
      @click="emits('confirm')">
      {{ t('确定') }}
    </span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    clearable?: boolean;
    /** 当前是否处于时间面板 */
    isTime?: boolean;
    showTime?: boolean;
    timeDisabled?: boolean;
  }

  type Emits = (e: 'clear' | 'confirm' | 'toggle-time') => void;

  const props = withDefaults(defineProps<Props>(), {
    clearable: true,
    isTime: false,
    showTime: false,
    timeDisabled: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 未选日期时不能切到时间面板
  const handleToggleTime = () => {
    if (props.timeDisabled) {
      return;
    }
    emits('toggle-time');
  };
</script>
