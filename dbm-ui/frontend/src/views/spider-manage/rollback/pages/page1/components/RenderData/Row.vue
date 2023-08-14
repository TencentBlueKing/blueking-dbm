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
    <tr>
      <td style="padding: 0;">
        <RenderCluster
          ref="clusterRef"
          :model-value="data.clusterData"
          @id-change="handleClusterIdChange" />
      </td>
      <td style="padding: 0;">
        <RenderMode
          ref="modeRef"
          :cluster-id="localClusterId"
          :rollback-time="data.rollbackTime" />
      </td>
      <td style="padding: 0;">
        <RenderDbName
          ref="databasesRef"
          :cluster-id="localClusterId"
          :model-value="data.databases" />
      </td>
      <td style="padding: 0;">
        <RenderDbName
          ref="databasesIgnoreRef"
          :cluster-id="localClusterId"
          :model-value="data.databasesIgnore"
          :required="false" />
      </td>
      <td style="padding: 0;">
        <RenderTableName
          ref="tablesRef"
          :cluster-id="localClusterId"
          :model-value="data.tables" />
      </td>
      <td style="padding: 0;">
        <RenderTableName
          ref="tablesIgnoreRef"
          :cluster-id="localClusterId"
          :model-value="data.tablesIgnore"
          :required="false" />
      </td>
      <td>
        <div class="action-box">
          <div
            class="action-btn"
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
  </tbody>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number,
      domain: string
      cloudId: number | null
    },
    rollbackupType: string,
    rollbackTime?: string,
    databases?: string[],
    databasesIgnore?: string [],
    tables?: string [],
    tablesIgnore?: string [],
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    clusterData: data.clusterData,
    rollbackupType: data.rollbackupType || 'REMOTE_AND_TIME',
    rollbackTime: data.rollbackTime,
    databases: data.databases,
    databasesIgnore: data.databasesIgnore,
    tables: data.tables,
    tablesIgnore: data.tablesIgnore,
  });
</script>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';

  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';
  import RenderTableName from '@views/mysql/common/edit-field/TableName.vue';

  import RenderCluster from './RenderCluster.vue';
  import RenderMode from './RenderMode.vue';

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
  const modeRef = ref();
  const databasesRef = ref();
  const databasesIgnoreRef = ref();
  const tablesRef = ref();
  const tablesIgnoreRef = ref();

  const localClusterId = ref(0);
  const localRollbackuoType = ref('');

  watch(() => props.data, () => {
    if (props.data.clusterData) {
      localClusterId.value = props.data.clusterData.id;
    }
    localRollbackuoType.value = props.data.rollbackupType;
  }, {
    immediate: true,
  });

  const handleClusterIdChange = (idData: { id: number, cloudId: number | null }) => {
    localClusterId.value = idData.id;
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
        modeRef.value.getValue(),
        databasesRef.value.getValue('databases'),
        tablesRef.value.getValue('tables'),
        databasesIgnoreRef.value.getValue('databases_ignore'),
        tablesIgnoreRef.value.getValue('tables_ignore'),
      ]).then(([
        clusterData,
        modeData,
        databasesData,
        tablesData,
        databasesIgnoreData,
        tablesIgnoreData,
      ]) => ({
        ...clusterData,
        ...modeData,
        ...databasesData,
        ...tablesData,
        ...databasesIgnoreData,
        ...tablesIgnoreData,
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
