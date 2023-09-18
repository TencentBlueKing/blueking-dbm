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
    {{ data.done_by }} {{ $t('处理完成') }}，
    {{ $t('操作') }}：<span :class="String(data.status).toLowerCase()">{{ getOperation(data) }}</span>，
    {{ $t('耗时') }}：{{ getCostTimeDisplay(data.cost_time) }}
    <template v-if="data.url">
      ，<a
        :href="data.url"
        :target="hrefTarget">{{ $t('查看详情') }} &gt;</a>
    </template>
    <p
      v-if="data.done_at"
      class="flow-time">
      {{ data.done_at }}
    </p>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { FlowItemTodo } from '@services/types/ticket';

  import { getCostTimeDisplay } from '@utils';

  interface Props {
    data: FlowItemTodo,
    hrefTarget: string
  }

  defineProps<Props>();

  const { t } = useI18n();

  const getOperation = (item: FlowItemTodo) => {
    const text = {
      DONE_SUCCESS: t('确认执行'),
      DONE_FAILED: t('终止单据'),
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
