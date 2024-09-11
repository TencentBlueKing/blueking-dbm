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
      <FixedColumn fixed="left">
        <RenderCluster
          ref="clusterRef"
          v-model="localClusterData"
          :unique="false" />
      </FixedColumn>
      <td style="padding: 0">
        <RenderDbName
          ref="fromDatabaseRef"
          v-model="localFromDatabase"
          check-not-exist
          :cluster-id="localClusterData?.id"
          :placeholder="$t('请输入单个源 DB 名')"
          single />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="toDatabaseRef"
          v-model="localToDatabase"
          check-exist
          :cluster-id="localClusterData?.id"
          :placeholder="$t('请输入单个新 DB 名')"
          single />
      </td>
      <OperateColumn
        :removeable="removeable"
        @add="handleAppend"
        @remove="handleRemove" />
    </tr>
  </tbody>
</template>
<script lang="ts">
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderDbName from '@views/sqlserver-manage/common/DbName.vue';
  import RenderCluster from '@views/sqlserver-manage/common/RenderCluster.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number;
    };
    fromDatabase: string;
    toDatabase: string;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    fromDatabase: data.fromDatabase || '',
    toDatabase: data.toDatabase || '',
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const clusterRef = ref();
  const fromDatabaseRef = ref();
  const toDatabaseRef = ref();

  const localClusterData = ref<IDataRow['clusterData']>();
  const localFromDatabase = ref<IDataRow['fromDatabase'][]>([]);
  const localToDatabase = ref<IDataRow['toDatabase'][]>([]);

  watch(
    () => props.data,
    () => {
      if (props.data.clusterData) {
        localClusterData.value = props.data.clusterData;
      }
      if (props.data.fromDatabase) {
        localFromDatabase.value = [props.data.fromDatabase];
      }
      if (props.data.toDatabase) {
        localToDatabase.value = [props.data.toDatabase];
      }
    },
    {
      immediate: true,
    },
  );

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
        clusterRef.value.getValue('cluster_id'),
        fromDatabaseRef.value.getValue('from_database'),
        toDatabaseRef.value.getValue('to_database'),
      ]).then(([clusterData, fromDatabaseData, toDatabaseData]) => ({
        ...clusterData,
        ...fromDatabaseData,
        ...toDatabaseData,
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
