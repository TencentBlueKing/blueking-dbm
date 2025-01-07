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
  <EditableColumn
    :label="t('当前规格')"
    :width="200">
    <template
      v-if="labelTip"
      #head>
      <BkPopover
        :content="labelTip"
        placement="top"
        theme="dark">
        <span class="spec-block-column-label-tip">{{ t('当前规格') }}</span>
      </BkPopover>
    </template>
    <EditableBlock :placeholder="placeholder">
      {{ data?.name ? `${data.name} ${showCounts ? t('((n))台', { n: data?.count }) : ''}` : '' }}
      <SpecPanel
        v-if="data.id"
        :data="data"
        :show-qps="showQps">
        <DbIcon
          class="visible-icon ml-4"
          type="visible1" />
      </SpecPanel>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import SpecPanel from './components/Panel.vue';

  interface Props {
    data?: ComponentProps<typeof SpecPanel>['data'];
    placeholder?: string;
    showCounts?: boolean;
    showQps?: boolean;
    labelTip?: string;
  }

  withDefaults(defineProps<Props>(), {
    data: undefined,
    placeholder: undefined,
    showCounts: true,
    showQps: false,
    labelTip: '',
  });

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .spec-block-column-label-tip {
    border-bottom: 1px dashed #979ba5;
  }

  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
