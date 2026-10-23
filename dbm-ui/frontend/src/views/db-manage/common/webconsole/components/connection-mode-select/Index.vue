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
  <div
    v-if="list.length"
    class="connection-mode-select">
    <div class="connection-mode-select-inner">
      <DbSelect
        :clearable="false"
        :disabled="disabled"
        :input-search="false"
        :list="list"
        :model-value="modelValue"
        @toggle="isActive = $event"
        @update:model-value="handleChange">
        <template #trigger="{ selected }">
          <div class="connection-mode-select-trigger">
            <div>{{ selected?.[0]?.label || '' }}</div>
            <DbIcon
              class="connection-mode-select-append"
              :class="{ 'is-active': isActive }"
              type="bk-dbm-icon db-icon-down-big" />
          </div>
        </template>
      </DbSelect>
    </div>
  </div>
  <span
    v-else
    class="connection-mode-select-status">
    {{ supportModeLoading ? t('加载中') : supportMode ? t('WebConsole_未启用模式') : '--' }}
  </span>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSupportWebconsoleMode } from '@services/source/dbbase';

  import type { WebconsoleMode } from '@views/db-manage/common/webconsole/types';

  interface Props {
    allowedModes: WebconsoleMode[];
    disabled?: boolean;
  }

  type Emits = (e: 'modes-change', modes: WebconsoleMode[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<WebconsoleMode>({
    required: true,
  });

  const { t } = useI18n();
  const { data: supportMode, loading: supportModeLoading } = useRequest(getSupportWebconsoleMode);
  const isActive = ref(false);
  // 环境启用不代表当前 DB 已实现，取两者交集。
  const list = computed(() =>
    [
      { enabled: supportMode.value?.http === true, label: 'HTTP', value: 'http' as const },
      { enabled: supportMode.value?.websocket === true, label: 'WebSocket', value: 'ws' as const },
    ].filter((item) => item.enabled && props.allowedModes.includes(item.value)),
  );

  watch(list, (modes) => emits('modes-change', modes.map((item) => item.value)), { immediate: true });

  const handleChange = (value: unknown) => {
    if (props.disabled || (value !== 'http' && value !== 'ws') || !list.value.some((item) => item.value === value)) {
      return;
    }
    modelValue.value = value;
  };
</script>
<style lang="less" scoped>
  .connection-mode-select {
    position: relative;
    display: flex;
    height: 40px;
    padding: 0 7px;
    align-items: center;

    &::after {
      position: absolute;
      top: 12px;
      right: 0;
      width: 1px;
      height: 16px;
      background: #45464d;
      content: '';
    }

    .connection-mode-select-inner {
      display: flex;
      height: 28px;
      padding: 0 6px;
      cursor: pointer;
      align-items: center;
      justify-content: center;

      &:hover {
        background: #424242;
        border-radius: 2px;
      }
    }

    .connection-mode-select-trigger {
      position: relative;
      display: flex;
      width: 96px;
      height: 28px;
      align-items: center;

      .connection-mode-select-append {
        position: absolute;
        right: 0;
        font-size: 16px;
        transition: transform 0.2s;

        &.is-active {
          transform: rotate(180deg);
        }
      }
    }
  }

  .connection-mode-select-status {
    margin: 0 8px;
    white-space: nowrap;
  }
</style>
