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
  <div class="selector-preview-result">
    <div class="header">
      <span>{{ t('结果预览') }}</span>
      <BkDropdown class="result-dropdown">
        <DbIcon type="bk-dbm-icon db-icon-more result-trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleClear">
              {{ t('清空所有') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopy">
              {{ t('复制所有访问入口') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
    <BkException
      v-if="data.length < 1"
      class="mt-50"
      :description="t('暂无数据_请从左侧添加对象')"
      scene="part"
      type="empty" />
    <div
      v-else
      class="result-wrapper db-scroll-y">
      <CollapseMini
        collapse
        :count="data.length">
        <div
          v-for="key of data"
          :key="key"
          class="result-item">
          <span
            v-overflow-tips
            class="text-overflow">
            {{ key }}
          </span>
          <DbIcon
            type="close result-item-remove"
            @click="handleRemove(key)" />
        </div>
      </CollapseMini>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  import { messageWarn } from '@utils';

  import CollapseMini from './CollapseMini.vue';

  interface Props {
    data: string[];
  }

  interface Emits {
    (e: 'remove', value: string): void;
    (e: 'clear'): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const copy = useCopy();

  const handleClear = () => {
    emits('clear');
  };

  const handleRemove = (key: string) => {
    emits('remove', key);
  };

  const handleCopy = () => {
    if (props.data.length < 1) {
      messageWarn(t('没有可复制集群'));
      return;
    }
    copy(props.data.join('\n'));
  };
</script>
<style lang="less">
  .selector-preview-result {
    display: flex;
    height: 100%;
    max-height: 625px;
    padding: 12px 24px;
    overflow: hidden;
    font-size: @font-size-mini;
    background-color: #f5f6fa;
    flex-direction: column;

    .header {
      display: flex;
      padding-bottom: 16px;
      align-items: center;

      > span {
        flex: 1;
        font-size: @font-size-normal;
        color: @title-color;
      }

      .result-dropdown {
        font-size: 0;
        line-height: 20px;
      }

      .result-trigger {
        display: block;
        font-size: 18px;
        color: @gray-color;
        cursor: pointer;

        &:hover {
          background-color: @bg-disable;
          border-radius: 2px;
        }
      }
    }

    .result-wrapper {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow-y: auto;

      .result-item {
        display: flex;
        padding: 0 12px;
        margin-bottom: 2px;
        line-height: 32px;
        background-color: @bg-white;
        border-radius: 2px;
        justify-content: space-between;
        align-items: center;

        .result-item-remove {
          display: none;
          font-size: @font-size-large;
          font-weight: bold;
          color: @gray-color;
          cursor: pointer;

          &:hover {
            color: @default-color;
          }
        }

        &:hover {
          .result-item-remove {
            display: block;
          }
        }
      }
    }
  }
</style>
