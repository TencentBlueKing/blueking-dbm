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
  <BkException
    v-if="isEmpty"
    class="mt-50"
    :description="t('暂无数据_请从左侧添加对象')"
    scene="part"
    type="empty" />
  <template v-else>
    <template
      v-for="(tabSelected, tabKey) in selectedMap"
      :key="tabKey">
      <CollapseMini
        v-if="tabSelected.length > 0"
        collapse
        :count="tabSelected.length"
        :title="getTabInfo(tabKey as string)">
        <div
          v-for="clusterItem in tabSelected"
          :key="_.get(clusterItem, getTabRowKey(tabKey as string))"
          class="result-item">
          <span
            v-overflow-tips
            v-test="{ type: 'span', value: 'clusterSelectorPreviewItem' }"
            class="text-overflow">
            {{ clusterItem[displayKey] }}
          </span>
          <div class="result-operations">
            <i
              class="db-icon-copy result-copy"
              @click="execCopy(clusterItem[displayKey])" />
            <i
              class="db-icon-close result-remove"
              @click="handleDeleteItem(clusterItem, tabKey as string)" />
          </div>
        </div>
      </CollapseMini>
    </template>
  </template>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  import type { SelectMapValueType } from '../../Index.vue';
  import { getTabRowKey } from '../tableConfig';

  import CollapseMini from './CollapseMini.vue';

  interface Props {
    displayKey?: string;
    selectedMap: SelectMapValueType<Record<string, any>>;
    showTitle?: boolean;
    tabList: { id: string; name: string }[];
  }

  type Emits = (e: 'delete', value: Record<string, any>, tabKey: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    displayKey: 'master_domain',
    showTitle: false,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(props.selectedMap), (clusterList) => clusterList.length === 0));

  // 获取 tab 信息
  const getTabInfo = (key: string) => (props.showTitle ? props.tabList.find((tab) => tab.id === key)?.name : '');

  const handleDeleteItem = (data: Record<string, any>, tabKey: string) => {
    emits('delete', data, tabKey);
  };
</script>

<style lang="less" scoped>
  .result-item {
    display: flex;
    align-items: center;
    padding: 0 12px;
    margin-bottom: 2px;
    line-height: 32px;
    background-color: @bg-white;
    border-radius: 2px;
    justify-content: space-between;

    &:hover {
      background: #e1ecff;

      .result-copy,
      .result-remove {
        display: block;
      }
    }

    .result-operations {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .result-copy {
      display: none;
      font-size: @font-size-mini;
      color: @gray-color;
      cursor: pointer;

      &:hover {
        color: @primary-color;
      }
    }

    .result-remove {
      display: none;
      font-size: @font-size-large;
      font-weight: bold;
      color: @gray-color;
      cursor: pointer;

      &:hover {
        color: @default-color;
      }
    }
  }
</style>
