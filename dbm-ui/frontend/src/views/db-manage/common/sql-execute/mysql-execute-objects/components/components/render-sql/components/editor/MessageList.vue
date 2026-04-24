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
    v-if="data.length > 0"
    class="sql-execute-error-message-list"
    :class="statusClass">
    <div class="message-total-wrapper">
      <DbIcon
        v-if="totalMap.errorNum > 0"
        style="margin-right: 4px; color: #b34747"
        type="delete-fill" />
      <DbIcon
        v-else
        style="margin-right: 4px; color: #ff9c01"
        type="early-warning" />
      <I18nT
        v-if="totalMap.errorNum"
        keypath="检测失败_共n个错误"
        tag="span">
        <span style="color: #b34747">{{ totalMap.errorNum }}</span>
      </I18nT>
      <template v-if="totalMap.warningNum > 0">
        <span v-if="totalMap.errorNum">，</span>
        <I18nT
          keypath="n个告警提示"
          tag="span">
          <span style="color: #ff9c01">{{ totalMap.warningNum }}</span>
        </I18nT>
      </template>
    </div>
    <div class="message-list-wrapper">
      <div
        v-for="(item, index) in data"
        :key="index"
        class="item-box">
        <div class="item-head">
          <DbIcon
            v-if="item.type === 'error'"
            style="color: #b34747"
            type="delete-fill" />
          <DbIcon
            v-else
            style="color: #e59e1e"
            type="early-warning" />
        </div>
        <div>
          <span>{{ item.message }}</span>
          <span class="error-line-number">[{{ item.line }}]</span>
        </div>
      </div>
    </div>
  </div>
  <div
    v-else
    class="sql-execute-error-message-list success-message">
    {{ t('检测通过') }}
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  export type IMessageList = Array<{ line: number; message: string; type: 'warning' | 'error' }>;

  interface Props {
    data: IMessageList;
  }

  const props = defineProps<Props>();
  const { t } = useI18n();

  const totalMap = computed(() => {
    let errorNum = 0;
    let warningNum = 0;
    props.data.forEach((item) => {
      if (item.type === 'error') {
        errorNum += 1;
      } else if (item.type === 'warning') {
        warningNum += 1;
      }
    });

    return {
      errorNum,
      warningNum,
    };
  });

  const statusClass = computed(() => {
    if (totalMap.value.errorNum > 0) {
      return 'is-error';
    }
    if (totalMap.value.warningNum > 0) {
      return 'is-warning';
    }
    return '';
  });
</script>
<style lang="less">
  .sql-execute-error-message-list {
    position: relative;
    height: 100%;
    overflow-y: auto;
    font-size: 12px;
    background: #212121;
    border-left: 4px solid #b34747;

    &.is-warning {
      border-left-color: #ff9c01;
    }

    &.success-message {
      display: flex;
      padding: 8px 16px;
      color: #3fc06d;
      border-left-color: #3fc06d;
      align-items: center;
    }

    .message-total-wrapper {
      padding: 8px 16px;
      color: #dcdee5;
    }

    .message-list-wrapper {
      padding: 0 0 12px;
      overflow-y: auto;

      .item-box {
        display: flex;
        padding: 4px 20px 4px 0;
        line-height: 16px;
        color: #dcdee5;
        cursor: pointer;
        align-items: flex-start;

        &:hover {
          background: #313238;
        }

        .item-head {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 16px;
          padding-right: 10px;
          padding-left: 16px;
        }

        .error-line-number {
          padding-left: 4px;
          color: #979ba5;
        }
      }
    }
  }
</style>
