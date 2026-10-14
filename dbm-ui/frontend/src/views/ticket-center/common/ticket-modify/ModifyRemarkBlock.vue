<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<!-- 修改说明：放在说明文案与变更表格之间，先看说明再看明细；改单页确认弹窗、确认修改弹窗、变更对比抽屉共用 -->
<template>
  <div class="ticket-modify-remark-block">
    <div class="ticket-modify-remark-block-title">{{ t('修改说明') }}</div>
    <div class="ticket-modify-remark-block-content">{{ content }}</div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    content: string;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .ticket-modify-remark-block {
    padding: 12px 16px;
    margin-bottom: 16px;
    font-size: 12px;
    line-height: 20px;
    background: #f5f7fa;
    border-radius: 2px;

    .ticket-modify-remark-block-title {
      margin-bottom: 4px;
      font-weight: bold;
      color: #313238;
    }

    .ticket-modify-remark-block-content {
      color: #63656e;
      word-break: break-all;
      white-space: pre-wrap;
    }
  }
</style>
