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
      <BkDropdown class="result-dropdown">
        <i class="db-icon-more result-trigger" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleClear">
              {{ t('清空所有') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyInstances">
              {{ t('复制所有实例') }}
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
      <template
        v-for="key in clusterTypes"
        :key="key">
        <CollapseMini
          v-if="lastValues[key]!.length > 0"
          :count="lastValues[key]!.length"
          :show-title="showTitle"
          :title="tabListMap[key]">
          <div
            v-for="(item, index) of lastValues[key]"
            :key="item.instance_address"
            class="result-item">
            <span
              v-overflow-tips
              v-test="{ type: 'span', value: 'instanceSelectorPreviewItem' }"
              class="text-overflow">
              {{ item.instance_address }}
            </span>
            <DbIcon
              type="close result-item-remove"
              @click="handleRemove(key, index)" />
          </div>
        </CollapseMini>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { execCopy, messageWarn } from '@utils';

  import type { InstanceModel, ISupportClusterType } from '../../types';
  import { tabListMap } from '../tabInfo';

  import CollapseMini from './CollapseMini.vue';

  export interface Props<C extends ISupportClusterType> {
    clusterTypes: C[];
    lastValues: { [key in C]: InstanceModel<C>[] };
  }

  type Emits = (e: 'change', value: Props<T>['lastValues']) => void;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isEmpty = computed(() =>
    Object.values<InstanceModel<T>[]>(props.lastValues).every((values) => values.length === 0),
  );
  const showTitle = computed(() => props.clusterTypes.length > 1);

  const handleClear = () => {
    if (isEmpty.value) {
      return;
    }
    emits(
      'change',
      Object.fromEntries(props.clusterTypes.map((key) => [key, [] as InstanceModel<T>[]])) as Props<T>['lastValues'],
    );
  };

  const handleRemove = (key: T, index: number) => {
    const target = [...props.lastValues[key]!];
    target.splice(index, 1);
    emits('change', {
      ...props.lastValues,
      [key]: target,
    });
  };

  const handleCopyInstances = () => {
    if (isEmpty.value) {
      messageWarn(t('没有可复制实例'));
      return;
    }

    const copyData = Object.values<InstanceModel<T>[]>(props.lastValues).flatMap((lastValuesItem) =>
      lastValuesItem.map((item) => item.instance_address),
    );
    execCopy(copyData.join('\n'), t('复制成功，共n条', { n: copyData.length }));
  };
</script>
<style lang="less">
  .instance-selector-preview-result {
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
