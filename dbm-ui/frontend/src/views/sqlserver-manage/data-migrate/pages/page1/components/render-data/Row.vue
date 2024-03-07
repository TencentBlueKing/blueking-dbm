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
      <td style="padding: 0">
        <RenderSrcCluster
          ref="srcClusterRef"
          v-model="localSrcClusterData" />
      </td>
      <td style="padding: 0">
        <RenderDstCluster
          ref="dstClusterRef"
          v-model="localDstClusterData"
          :src-cluster-data="localSrcClusterData" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="dbNameRef"
          v-model="localDbName"
          check-not-exist
          :cluster-id="localSrcClusterData?.id" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="ignoreDbNameRef"
          v-model="localDbIgnoreName"
          :cluster-id="localSrcClusterData?.id"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderRename
          ref="renameDbNameRef"
          v-model:db-ignore-name="localDbIgnoreName"
          v-model:db-name="localDbName"
          :cluster-data="localSrcClusterData"
          :dst-cluster-data="localDstClusterData" />
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
              disabled: removeable,
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
    srcClusterData?: {
      id: number;
      domain: string;
      cloudId: number;
      majorVersion: string;
    };
    dstClusterData?: {
      id: number;
      domain: string;
      cloudId: number;
    };
    dbList: string[];
    ignoreDbList: string[];
    renameInfos: {
      db_name: string;
      target_db_name: string;
      rename_db_name: string;
    }[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    srcClusterData: data.srcClusterData,
    dstClusterData: data.dstClusterData,
    dbList: data.dbList || [],
    ignoreDbList: data.ignoreDbList || [],
    renameInfos: data.renameInfos || [],
  });
</script>
<script setup lang="ts">
  import { ref, watch } from 'vue';

  import RenderDbName from '@views/sqlserver-manage/common/DbName.vue';

  import RenderDstCluster from './RenderDstCluster.vue';
  import RenderRename from './RenderRename.vue';
  import RenderSrcCluster from './RenderSrcCluster.vue';

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

  const srcClusterRef = ref<InstanceType<typeof RenderSrcCluster>>();
  const dstClusterRef = ref<InstanceType<typeof RenderDstCluster>>();
  const dbNameRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbNameRef = ref<InstanceType<typeof RenderDbName>>();
  const renameDbNameRef = ref<InstanceType<typeof RenderRename>>();

  const localSrcClusterData = ref<IDataRow['srcClusterData']>();
  const localDstClusterData = ref<IDataRow['dstClusterData']>();
  const localDbName = ref<string[]>([]);
  const localDbIgnoreName = ref<string[]>([]);

  watch(
    () => props.data,
    () => {
      localSrcClusterData.value = props.data.srcClusterData;
      localDstClusterData.value = props.data.dstClusterData;
      localDbName.value = props.data.dbList;
      localDbIgnoreName.value = props.data.ignoreDbList;
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
        srcClusterRef.value!.getValue('src_cluster'),
        dstClusterRef.value!.getValue('dst_cluster'),
        dbNameRef.value!.getValue('db_list'),
        ignoreDbNameRef.value!.getValue('ignore_db_list'),
        renameDbNameRef.value!.getValue(),
      ]).then(([srcClusterData, dstClusterData, databasesData, tablesData, dbIgnoreNameData]) => ({
        ...srcClusterData,
        ...dstClusterData,
        ...databasesData,
        ...tablesData,
        ...dbIgnoreNameData,
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
