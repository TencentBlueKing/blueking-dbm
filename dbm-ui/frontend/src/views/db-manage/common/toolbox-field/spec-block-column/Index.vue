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
  <EditableTableColumn
    :label="t('当前规格')"
    :width="200">
    <EditBlock :placeholder="placeholder">
      {{ data?.name ? `${data.name} ${isIgnoreCounts ? '' : t('((n))台', { n: data?.count })}` : '' }}
      <SpecPanel
        v-if="data"
        :data="data"
        :hide-qps="hideQps">
        <DbIcon
          class="visible-icon ml-4"
          type="visible1" />
      </SpecPanel>
    </EditBlock>
  </EditableTableColumn>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { Block as EditBlock, Column as EditableTableColumn } from '@components/editable-table/Index.vue';

  import SpecPanel from './components/Panel.vue';

  interface Props {
    data?: ComponentProps<typeof SpecPanel>['data'];
    isIgnoreCounts?: boolean;
    placeholder?: string;
    hideQps?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    data: undefined,
    placeholder: undefined,
    isIgnoreCounts: false,
    hideQps: true,
  });

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
