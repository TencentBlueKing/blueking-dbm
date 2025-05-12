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
  <div class="panel-row mt-4">
    <div class="row-column row-column-left">
      <template v-if="slots.left">
        <div class="column-title">{{ leftLabel || t('当前text', { text: label }) }}：</div>
        <div class="column-content">
          <slot name="left" />
        </div>
      </template>
    </div>
    <div class="row-column row-column-right">
      <template v-if="slots.right">
        <div class="column-title">{{ rightLabel || t('目标text', { text: label }) }}：</div>
        <div class="column-content">
          <slot name="right" />
        </div>
      </template>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    label?: string;
    leftLabel?: string;
    rightLabel?: string;
  }

  interface Slots {
    left(): VNode;
    right(): VNode;
  }

  withDefaults(defineProps<Props>(), {
    label: '',
    leftLabel: '',
    rightLabel: '',
  });

  const slots = defineSlots<Slots>();

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .panel-row {
    display: flex;
    width: 100%;

    .row-column-left {
      width: 35%;
    }

    .row-column-right {
      width: 65%;
    }

    .row-column {
      display: flex;
      align-items: center;

      .column-title {
        width: 100px;
        height: 18px;
        font-size: 12px;
        line-height: 18px;
        letter-spacing: 0;
        color: #63656e;
        text-align: right;
      }

      .column-content {
        display: flex;
        font-size: 12px;
        color: #63656e;
        flex: 1;

        :deep(.render-spec-box) {
          height: 100%;
          padding: 0;
          line-height: 22px;
        }

        .number-style {
          margin-left: 2px;
          font-size: 12px;
          font-weight: bold;
          color: #313238;
        }
      }
    }
  }
</style>
