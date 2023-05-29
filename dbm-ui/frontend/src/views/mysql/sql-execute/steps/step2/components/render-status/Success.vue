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
  <div class="sql-execute-success">
    <div class="wrapper">
      <span class="success-flag">
        <DbIcon type="check-circle-fill" />
      </span>
    </div>
    <div style="margin-top: 22px; font-size: 24px; line-height: 32px; color: #313238">
      {{ $t('模拟执行成功') }}
    </div>
    <div style="margin-top: 8px; line-height: 32px; color: #313238">
      {{ $t('接下你可以直接_提交申请_或返回上一步修改重试') }}
    </div>
    <div class="action-wrapper">
      <div class="confirm-action">
        <span>{{ $t('生产执行时无需再确认') }}</span>
        <BkSwitcher
          size="small"
          style="margin-left: 12px"
          theme="primary" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts"></script>
<style lang="less" scoped>
  .sql-execute-success {
    padding-top: 40px;
    text-align: center;

    .wrapper {
      display: flex;
      align-items: center;
      justify-content: center;

      .success-flag {
        display: flex;
        width: 64px;
        height: 64px;
        font-size: 64px;
        color: #2dcb56;
      }
    }

    .action-wrapper {
      display: flex;
      justify-content: center;
    }

    .confirm-action {
      display: flex;
      align-items: center;
      height: 40px;
      padding: 0 32px;
      margin-top: 10px;
      font-size: 12px;
      color: #63656e;
      background: #f5f7fa;
      border-radius: 20px;
    }
  }
</style>
