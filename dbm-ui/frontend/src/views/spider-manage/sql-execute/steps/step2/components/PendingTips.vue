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
  <div class="sql-execute-pending">
    <div class="wrapper">
      <span class="loading-flag">
        <DbIcon
          svg
          type="sync-pending" />
      </span>
    </div>
    <div style="margin-top: 22px; font-size: 24px; line-height: 32px; color: #313238">
      {{ t('模拟执行正在进行中_请稍等') }}
    </div>
    <div style="margin-top: 8px; line-height: 32px; color: #313238">
      {{ t('执行成功后_自动提交单据申请_无需等待') }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .sql-execute-pending {
    padding-top: 40px;
    text-align: center;

    .wrapper {
      display: flex;
      align-items: center;
      justify-content: center;

      .loading-flag {
        display: flex;
        width: 64px;
        height: 64px;
        font-size: 64px;
        color: #3a84ff;
        animation: rotate-loading 1s linear infinite;
      }
    }
  }
</style>
