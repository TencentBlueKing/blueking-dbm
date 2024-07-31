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
  <div class="flow-todo__infos">
    <div
      v-if="isSystemHandled"
      style="color: #ea3636">
      <I18nT keypath="U_已处理_A">
        <span>{{ data.done_by }}</span>
        <span>
          {{ t('超过n小时自动终止', { n: (content.context.expire_time ?? 0) * 24 }) }}
        </span>
      </I18nT>
    </div>
    <I18nT
      v-else
      keypath="U_已处理_A_耗时_T">
      <span>{{ data.done_by }}</span>
      <span>{{ getOperation(data) }}</span>
      <span>{{ getCostTimeDisplay(data.cost_time) }}</span>
    </I18nT>
    <template v-if="data.url">
      ，
      <a
        :href="data.url"
        :target="hrefTarget">
        {{ $t('查看详情') }} &gt;
      </a>
    </template>
    <div
      v-if="data.done_at"
      class="flow-time">
      {{ utcDisplayTime(data.done_at) }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { FlowItem, FlowItemTodo } from '@services/types/ticket';

  import { getCostTimeDisplay, utcDisplayTime } from '@utils';

  interface Props {
    content: FlowItem;
    data: FlowItemTodo;
    hrefTarget: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isSystemHandled = computed(() => props.data.done_by === 'system');

  const getOperation = (item: FlowItemTodo) => {
    const text = {
      DONE_SUCCESS: item.type === 'RESOURCE_REPLENISH' ? t('重试') : t('确认执行'),
      DONE_FAILED: t('人工终止'),
      RUNNING: '--',
      TODO: '--',
    };
    return text[item.status];
  };
</script>

<style lang="less" scoped>
  .flow-todo__infos {
    margin-bottom: 8px;

    .done_success {
      color: @success-color;
    }

    .done_failed {
      color: @danger-color;
    }
  }
</style>
