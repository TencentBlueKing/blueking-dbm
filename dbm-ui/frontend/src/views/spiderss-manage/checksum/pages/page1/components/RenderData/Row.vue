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
  <tbody>
    <template
      v-for="(clusterDataItem, index) in data.backupInfos"
      :key="index">
      <tr>
        <td
          v-if="index === 0"
          :rowspan="data.backupInfos.length"
          style="padding: 0;">
          <RenderCluster
            ref="clusterRef"
            :model-value="data.clusterData"
            @id-change="handleClusterIdChange" />
        </td>
        <td
          v-if="index === 0"
          :rowspan="data.backupInfos.length"
          style="padding: 0;">
          <RenderScope
            ref="scopeRef"
            :model-value="data.scope"
            @change="handleScopeChange" />
        </td>
        <td style="padding: 0;">
          <RenderSlave
            ref="slaveRef"
            :cluster-id="localClusterId"
            :model-value="clusterDataItem.slave"
            :scope="localScope" />
        </td>
        <td style="padding: 0;">
          <RenderMaster
            ref="RenderMaster"
            :cluster-id="localClusterId"
            :model-value="clusterDataItem.master"
            :scope="localScope" />
        </td>
        <td style="padding: 0;">
          <RenderDbName
            ref="dbPatternsRef"
            :cluster-id="localClusterId"
            :model-value="clusterDataItem.ignoreDbs" />
        </td>
        <td style="padding: 0;">
          <RenderDbName
            ref="ignoreDbsRef"
            :cluster-id="localClusterId"
            :model-value="clusterDataItem.ignoreDbs"
            :required="false" />
        </td>
        <td style="padding: 0;">
          <RenderTableName
            ref="tablePatternsRef"
            :cluster-id="localClusterId"
            :model-value="clusterDataItem.tablePatterns" />
        </td>
        <td style="padding: 0;">
          <RenderTableName
            ref="ignoreTablesRef"
            :cluster-id="localClusterId"
            :model-value="clusterDataItem.ignoreTables"
            :required="false" />
        </td>
        <td>
          <div class="action-box">
            <div
              class="action-btn ml-2"
              @click="handleAppend">
              <DbIcon type="plus-fill" />
            </div>
            <div
              class="action-btn"
              :class="{
                disabled: removeable
              }"
              @click="handleRemove">
              <DbIcon type="minus-fill" />
            </div>
          </div>
        </td>
      </tr>
    </template>
  </tbody>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number,
      domain: string,
    },
    scope: string,
    backupInfos: {
      master: string,
      slave: string,
      dbPatterns?: string [],
      ignoreDbs?: string [],
      tablePatterns?: string [],
      ignoreTables?: string [],
    }[],
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => {
    const backupInfos = data.backupInfos ? data.backupInfos[0] : {} as IDataRow['backupInfos'][0];
    return ({
      rowKey: random(),
      clusterData: data.clusterData,
      scope: data.scope || 'all',
      backupInfos: [
        {
          master: backupInfos.master || '',
          slave: backupInfos.slave || '',
          dbPatterns: backupInfos.dbPatterns,
          tablePatterns: backupInfos.tablePatterns,
          ignoreDbs: backupInfos.ignoreDbs,
          ignoreTables: backupInfos.ignoreTables,
        },
      ],
    });
  };

</script>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';

  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/mysql/common/edit-field/TableName.vue';

  import RenderCluster from './RenderCluster.vue';
  import RenderMaster from './RenderMaster.vue';
  import RenderScope from './RenderScope.vue';
  import RenderSlave from './RenderSlave.vue';

  interface Props {
    data: IDataRow,
    removeable: boolean,
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
  }

  interface Exposes{
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const scopeRef = ref();
  const slaveRef = ref();
  const masterRef = ref();
  const dbPatternsRef = ref();
  const ignoreDbsRef = ref();
  const tablePatternsRef = ref();
  const ignoreTablesRef = ref();

  const localClusterId = ref(0);
  const localScope = ref('');

  watch(() => props.data, () => {
    if (props.data.clusterData) {
      localClusterId.value = props.data.clusterData.id;
    }
    if (props.data.scope) {
      localScope.value = props.data.scope;
    }
  }, {
    immediate: true,
  });

  const handleClusterIdChange = (clusterId: number) => {
    localClusterId.value = clusterId;
  };
  const handleScopeChange = (scope: string) => {
    localScope.value = scope;
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        clusterRef.value.getValue(),
        scopeRef.value.getValue(),
        slaveRef.value.getValue(),
        masterRef.value.getValue(),
        dbPatternsRef.value.getValue('db_patterns'),
        tablePatternsRef.value.getValue('table_patterns'),
        ignoreDbsRef.value.getValue('ignore_dbs'),
        ignoreTablesRef.value.getValue('ignore_tables'),
      ]).then(([
        clusterData,
        scopeData,
        slaveData,
        masterData,
        dbPatternsData,
        tablePatternsData,
        ignoreDbsData,
        ignoreTablesData,
      ]) => ({
        ...clusterData,
        ...scopeData,
        ...slaveData,
        ...masterData,
        ...dbPatternsData,
        ...tablePatternsData,
        ...ignoreDbsData,
        ...ignoreTablesData,
      }));
    },
  });
</script>
<style lang="less" scoped>
.action-box {
  display: flex;
  align-items: center;

  .action-btn {
    display: flex;
    font-size: 14px;
    color: #c4c6cc;
    cursor: pointer;
    transition: all 0.15s;

    &:hover {
      color: #979ba5;
    }

    &.disabled {
      color: #dcdee5;
      cursor: not-allowed;
    }

    & ~ .action-btn {
      margin-left: 18px;
    }
  }
}
</style>
