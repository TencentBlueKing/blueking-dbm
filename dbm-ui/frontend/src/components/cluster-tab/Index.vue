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
    class="cluster-tab"
    type="unborder-card">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.id"
      :label="tab.name"
      :name="tab.id" />
  </BkTab>
</template>

<script setup lang="ts">
  import { useFunController, useUserProfile } from '@stores';

  import { clusterTypeInfos, ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

  interface Props {
    excludes?: ClusterTypes[];
  }

  const props = withDefaults(defineProps<Props>(), {
    excludes: () => [],
  });

  const moduleValue = defineModel<ClusterTypes>();

  const funControllerStore = useFunController();
  const userProfileStore = useUserProfile();

  let renderTabs: {
    id: ClusterTypes;
    name: string;
  }[] = [];
  const tabsInfo = Object.values(clusterTypeInfos).reduce<
    {
      id: ClusterTypes;
      name: string;
    }[]
  >((result, item) => {
    const { dbType, id, moduleId, name } = item;
    const data = funControllerStore.funControllerData.getFlatData(moduleId);
    if (props.excludes.includes(id)) {
      return result;
    }
    if (data[dbType as keyof typeof data]) {
      result.push({ id, name });
    }
    return result;
  }, []);

  const topDbTypes: string[] = userProfileStore.profile[UserPersonalSettings.TOP_DB_TYPES] || [];
  if (topDbTypes.length > 0) {
    const tabInfoMap = Object.fromEntries(tabsInfo.map((resultItem) => [resultItem.id, resultItem]));
    const dbTypeMap = tabsInfo.reduce(
      (prev, item) => {
        const dbType = clusterTypeInfos[item.id].dbType;
        if (prev[dbType]) {
          return Object.assign(prev, {
            [dbType]: prev[dbType].concat(item.id),
          });
        }
        return Object.assign(prev, {
          [dbType]: [item.id],
        });
      },
      {} as Record<DBTypes, ClusterTypes[]>,
    );

    const topList = topDbTypes.flatMap((topItem) => {
      const topClusterTypes = dbTypeMap[topItem as DBTypes];
      return topClusterTypes.map((topClusterType) => tabInfoMap[topClusterType]);
    });
    const topMap = Object.fromEntries(topList.map((item) => [item.id, true]));
    const commonList = tabsInfo.filter((item) => !topMap[item.id]);
    renderTabs = topList.concat(commonList);
  } else {
    renderTabs = tabsInfo;
  }
</script>

<style lang="less">
  .cluster-tab {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content {
      display: none;
    }
  }
</style>
