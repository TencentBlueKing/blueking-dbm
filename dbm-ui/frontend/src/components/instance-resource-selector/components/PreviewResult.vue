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
  <div class="instance-resource-selector-preview-result">
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
        v-for="[bizId, items] in Object.entries(groupByBiz)"
        :key="bizId">
        <CollapseMini
          v-if="items.length > 0"
          collapse
          :count="items.length"
          :title="getBizInfoById(Number(bizId))?.name || `${t('业务')}${bizId}`">
          <div
            v-for="item of items"
            :key="item.instance_address"
            class="result-item">
            <span
              v-overflow-tips
              class="text-overflow">
              {{ item.instance_address }}
            </span>
            <DbIcon
              type="close result-item-remove"
              @click="() => handleRemove(item as IValue)" />
          </div>
        </CollapseMini>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { execCopy, messageWarn } from '@utils';

  import CollapseMini from './CollapseMini.vue';
  import { type IValue } from './RenderTable.vue';

  const selected = defineModel<IValue[]>('selected', {
    required: true,
  });

  const { t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();

  const groupByBiz = computed(() => _.groupBy([...selected.value], 'bk_biz_id'));
  const isEmpty = computed(() => selected.value.length === 0);

  const handleClear = () => {
    selected.value = [];
  };

  const handleRemove = (item: IValue) => {
    selected.value = selected.value.filter((cur) => cur.instance_address !== item.instance_address);
  };

  const handleCopy = () => {
    if (isEmpty.value) {
      messageWarn(t('没有可复制实例'));
      return;
    }

    const copyData = selected.value.map((item) => item.instance_address);
    execCopy(copyData.join('\n'), t('复制成功，共n条', { n: copyData.length }));
  };
</script>
<style lang="less">
  .instance-resource-selector-preview-result {
    display: flex;
    height: 100%;
    max-height: 680px;
    padding: 12px 24px;
    overflow: hidden;
    font-size: @font-size-mini;
    background-color: #f5f6fa;
    flex-direction: column;

    .header {
      display: flex;
      padding: 16px 0;
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
