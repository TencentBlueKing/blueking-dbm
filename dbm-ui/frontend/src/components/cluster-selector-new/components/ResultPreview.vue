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
    :description="$t('暂无数据_请从左侧添加对象')"
    scene="part"
    type="empty" />
  <template v-else>
    <template
      v-for="(tabSelected, tabKey) in selectedMap"
      :key="tabKey">
      <CollapseMini
        v-if="Object.keys(tabSelected).length > 0"
        collapse
        :count="Object.keys(tabSelected).length"
        :title="getTabInfo(tabKey)">
        <div
          v-for="clusterItem in tabSelected"
          :key="clusterItem.id"
          class="result__item">
          <span
            v-overflow-tips
            class="text-overflow">{{ clusterItem.master_domain }}</span>
          <i
            class="db-icon-close result__remove"
            @click="handleDeleteItem(clusterItem, false)" />
        </div>
      </CollapseMini>
    </template>
  </template>
</template>
<script setup lang="tsx" generic="T extends SpiderModel">
  import _ from 'lodash';

  import SpiderModel from '@services/model/spider/spider';

  import CollapseMini from './CollapseMini.vue';

  type Selected = Record<string, T[]>;

  interface Props {
    tabList: { name: string; id: string }[],
    selectedMap: Record<string, Record<string, ValueOf<Selected>[0]>>,
    showTitle?: boolean,
  }

  interface Emits {
    (e: 'delete-item', value: T, status: boolean): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    showTitle: true,
  });

  const emits = defineEmits<Emits>();

  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(props.selectedMap), item => Object.keys(item).length < 1));

  // 获取 tab 信息
  const getTabInfo = (key: string) => (props.showTitle ? props.tabList.find(tab => tab.id === key)?.name : '');

  const handleDeleteItem = (data: ValueOf<Selected>[0], value: boolean) => {
    emits('delete-item', data, value);
  };


</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .result__item {
    padding: 0 12px;
    margin-bottom: 2px;
    line-height: 32px;
    background-color: @bg-white;
    border-radius: 2px;
    justify-content: space-between;
    .flex-center();

    .result__remove {
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
      .result__remove {
        display: block;
      }
    }
  }

</style>
