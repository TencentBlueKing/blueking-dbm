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
    class="db-tab"
    type="unborder-card">
    <BkTabPanel
      v-for="tab of renderTabs"
      :key="tab.name"
      :label="tab.label"
      :name="tab.name" />
  </BkTab>
</template>

<script setup lang="ts">
  import type { ControllerBaseInfo } from '@services/model/function-controller/functionController';

  import { useFunController } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  interface TabItem {
    label: string;
    name: DBTypes;
  }

  const funControllerStore = useFunController();

  const moduleValue = defineModel<DBTypes>({
    default: DBTypes.MYSQL,
  });

  const renderTabs = Object.values(DBTypeInfos).reduce((result, item) => {
    const { id: dbType, name, moduleId } = item;
    const data = funControllerStore.funControllerData[moduleId];
    if (dbType === moduleId && data?.is_enabled) {
      result.push({
        label: name,
        name: dbType,
      });
    } else {
      const children = data?.children as Record<DBTypes, ControllerBaseInfo>;
      if (children[dbType]?.is_enabled) {
        result.push({
          label: name,
          name: dbType,
        });
      }
    }
    return result;
  }, [] as TabItem[]);
</script>

<style lang="less">
  .db-tab {
    padding: 0 24px;
    background: #fff;
    box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

    .bk-tab-content {
      display: none;
    }
  }
</style>
