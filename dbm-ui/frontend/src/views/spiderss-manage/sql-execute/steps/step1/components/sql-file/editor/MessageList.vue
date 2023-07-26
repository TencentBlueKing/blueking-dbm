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
    class="sql-execute-error-message-list">
    <div
      v-if="isFolded"
      class="message-total-wrapper"
      @click="handleShowError">
      <DbIcon
        style="margin-right: 4px; color: #b34747;"
        type="delete-fill" />
      <I18nT
        v-if="totalMap.errorNum"
        keypath="检测失败_共n个错误"
        tag="span">
        <span style="color: #b34747;">{{ totalMap.errorNum }}</span>
      </I18nT>
      <template v-if="totalMap.warningNum > 0">
        <span v-if="totalMap.errorNum">，</span>
        <I18nT
          keypath="n个告警提示"
          tag="span">
          <span style="color: #ff9c01;">{{ totalMap.warningNum }}</span>
        </I18nT>
      </template>
    </div>
    <div
      v-else
      class="message-list-wrapper">
      <div
        v-for="(item, index) in data"
        :key="index"
        class="item-box">
        <div class="item-head">
          <DbIcon
            v-if="item.type === 'error'"
            style="color: #b34747;"
            type="delete-fill" />
          <DbIcon
            v-else
            style="color: #e59e1e;"
            type="early-warning" />
        </div>
        <div>
          <span>{{ item.message }}</span>
          <span class="error-line-number">[{{ item.line }}]</span>
        </div>
      </div>
    </div>
    <div
      class="toggle-btn"
      @click="handleToogle">
      <DbIcon
        v-if="isFolded"
        type="up-big" />
      <DbIcon
        v-else
        type="down-big" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    computed,
    ref,
  } from 'vue';

  export type IMessageList = Array<{ type: 'warning' | 'error', line: number, message: string }>

  interface Props {
    modelValue: boolean,
    data: IMessageList;
  }

  interface Emits{
    (e: 'update:modelValue', value: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isFolded = ref(props.modelValue);
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

  const handleShowError = () => {
    isFolded.value = false;
    emits('update:modelValue', false);
  };

  const handleToogle = () => {
    isFolded.value = !isFolded.value;
    emits('update:modelValue', isFolded.value);
  };
</script>
<style lang="less">
  .sql-execute-error-message-list {
    position: relative;
    height: 100%;
    overflow-y: auto;
    font-size: 12px;
    background: #212121;
    border-left: 4px solid #b34747;

    .message-total-wrapper {
      padding: 8px 16px;
      color: #dcdee5;
      cursor: pointer;
    }

    .message-list-wrapper {
      padding: 12px 0;
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

    .toggle-btn {
      position: absolute;
      top: 0;
      right: 10px;
      display: flex;
      width: 30px;
      height: 30px;
      font-size: 18px;
      color: #dcdee5;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }
  }
</style>
