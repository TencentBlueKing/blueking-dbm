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
  <div class="instance-selector-preview-result">
    <div class="header">
      <span>{{ t('结果预览') }}</span>
      <BkDropdown>
        <DbIcon
          class="result-trigger"
          type="more" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleClear">
              {{ t('清空所有') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAllIp">
              {{ t('复制所有IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
    <BkException
      v-if="isEmpty"
      class="mt-50"
      :description="t('暂无数据_请从左侧添加对象')"
      scene="part"
      type="empty" />
    <div
      v-else
      class="result-wrapper db-scroll-y">
      <CollapseMini
        v-if="lastValues.length > 0"
        collapse
        :count="lastValues.length"
        :title="t('资源池')">
        <div
          v-for="(item, index) in lastValues"
          :key="index"
          class="result-item">
          <span
            v-overflow-tips
            class="text-overflow">
            {{ item.ip }}
          </span>
          <DbIcon
            class="result-item-remove"
            type="close"
            @click="handleRemove(index)" />
        </div>
      </CollapseMini>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { useCopy } from '@hooks';

  import { messageWarn } from '@utils';

  import CollapseMini from './components/CollapseMini.vue';

  interface Props {
    lastValues: DbResourceModel[];
  }

  interface Emits {
    (e: 'change', value: DbResourceModel[]): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const copy = useCopy();

  const isEmpty = computed(() => props.lastValues.length === 0);

  const handleClear = () => {
    emits('change', []);
  };

  const handleRemove = (index: number) => {
    const target = props.lastValues;
    target.splice(index, 1);
    emits('change', target);
  };

  const handleCopyAllIp = () => {
    if (isEmpty.value) {
      messageWarn(t('没有可复制IP'));
      return;
    }
    copy(props.lastValues.map((item) => item.ip).join('\n'));
  };
</script>

<style lang="less">
  .instance-selector-preview-result {
    display: flex;
    height: 100%;
    height: 625px;
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
