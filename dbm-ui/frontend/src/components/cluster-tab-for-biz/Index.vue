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
  <BkTab
    v-model:active="moduleValue"
    class="cluster-tab-for-biz"
    type="unborder-card">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id" />
  </BkTab>
</template>

<script setup lang="ts">
  import { useBizDbDisplay } from '@hooks';

  import { type ClusterTypeInfoItem, clusterTypeInfos, ClusterTypes } from '@common/const';

  interface Props {
    excludes?: ClusterTypes[];
  }

  const props = withDefaults(defineProps<Props>(), {
    excludes: () => [],
  });

  const moduleValue = defineModel<ClusterTypes>();
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { tabList } = useBizDbDisplay();

  // dbType 和 clusterTypeInfo 的对应关系
  const dbClusterMap = Object.entries(clusterTypeInfos).reduce<Record<string, ClusterTypeInfoItem[]>>(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    (prev, [clusterType, clusterInfo]) => {
      if (prev[clusterInfo.dbType]) {
        return Object.assign(prev, {
          [clusterInfo.dbType]: prev[clusterInfo.dbType].concat(clusterInfo),
        });
      }
      return Object.assign(prev, { [clusterInfo.dbType]: [clusterInfo] });
    },
    {},
  );

  const renderTabs = computed(() =>
    tabList.value.reduce<ClusterTypeInfoItem[]>((result, item) => {
      const clusterList = dbClusterMap[item.id];
      const includeList = clusterList.filter((item) => !props.excludes.includes(item.id));
      return result.concat(includeList);
    }, []),
  );

  watch(
    () => renderTabs.value.length,
    () => {
      isShow.value = renderTabs.value.length > 0;
    },
  );
</script>

<style lang="less">
  .cluster-tab-for-biz {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content {
      display: none;
    }
  }
</style>
