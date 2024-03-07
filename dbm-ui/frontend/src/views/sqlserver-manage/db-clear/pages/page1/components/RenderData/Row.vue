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
        <RenderCluster
          ref="clusterRef"
          v-model="localClusterData" />
      </td>
      <td style="padding: 0">
        <RenderClearMode
          ref="clearModeRef"
          :model-value="localCleanMode" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="cleanDbsPatternsRef"
          v-model="localCleanDbsPatterns"
          check-not-exist
          :cluster-id="localClusterData?.id" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="cleanIgnoreDbsPatternsRef"
          v-model="localCleanIgnoreDbsPatterns"
          check-not-exist
          :cluster-id="localClusterData?.id"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="cleanTablesRef"
          :cluster-id="localClusterData?.id"
          :model-value="data.cleanTables" />
      </td>
      <td style="padding: 0">
        <RenderTableName
          ref="ignoreCleanTablesRef"
          :cluster-id="localClusterData?.id"
          :model-value="data.ignoreCleanTables"
          :required="false" />
      </td>
      <td style="padding: 0">
        <RenderClearDbName
          ref="cleanDbsRef"
          v-model:cleanDbsPatterns="localCleanDbsPatterns"
          v-model:cleanIgnoreDbsPatterns="localCleanIgnoreDbsPatterns"
          :cluster-data="localClusterData" />
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
    clusterData?: {
      id: number;
      domain: string;
      cloudId: number;
    };
    cleanMode: string;
    cleanDbsPatterns: string[];
    cleanIgnoreDbsPatterns: string[];
    cleanTables: string[];
    ignoreCleanTables: string[];
    cleanDbs: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>): IDataRow => ({
    rowKey: random(),
    clusterData: data.clusterData,
    cleanMode: data.cleanMode || '',
    cleanDbsPatterns: data.cleanDbsPatterns || [],
    cleanIgnoreDbsPatterns: data.cleanIgnoreDbsPatterns || [],
    cleanTables: data.cleanTables || ['*'],
    ignoreCleanTables: data.ignoreCleanTables || [],
    cleanDbs: data.cleanDbs || [],
  });
</script>
<script setup lang="ts">
  import RenderDbName from '@views/sqlserver-manage/common/DbName.vue';
  import RenderTableName from '@views/sqlserver-manage/common/TableName.vue';

  import RenderClearDbName from './RenderClearDbName.vue';
  import RenderClearMode from './RenderClearMode.vue';
  import RenderCluster from './RenderCluster.vue';

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

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const clearModeRef = ref<InstanceType<typeof RenderClearMode>>();
  const cleanDbsPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const cleanIgnoreDbsPatternsRef = ref<InstanceType<typeof RenderDbName>>();
  const cleanTablesRef = ref<InstanceType<typeof RenderTableName>>();
  const ignoreCleanTablesRef = ref<InstanceType<typeof RenderTableName>>();
  const cleanDbsRef = ref<InstanceType<typeof RenderClearDbName>>();

  const localClusterData = ref<IDataRow['clusterData']>();
  const localCleanMode = ref<IDataRow['cleanMode']>('');
  const localCleanDbsPatterns = ref<IDataRow['cleanDbsPatterns']>([]);
  const localCleanIgnoreDbsPatterns = ref<IDataRow['cleanIgnoreDbsPatterns']>([]);

  watch(
    () => props.data,
    () => {
      localClusterData.value = props.data.clusterData;
      localCleanMode.value = props.data.cleanMode;
      localCleanDbsPatterns.value = props.data.cleanDbsPatterns;
      localCleanIgnoreDbsPatterns.value = props.data.cleanIgnoreDbsPatterns;
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
        clusterRef.value!.getValue(),
        clearModeRef.value!.getValue(),
        cleanDbsPatternsRef.value!.getValue('clean_dbs_patterns'),
        cleanIgnoreDbsPatternsRef.value!.getValue('clean_ignore_dbs_patterns'),
        cleanTablesRef.value!.getValue('clean_tables'),
        ignoreCleanTablesRef.value!.getValue('ignore_clean_tables'),
        cleanDbsRef.value!.getValue(),
      ]).then(
        ([
          clusterData,
          clearModeData,
          cleanDbsPatternsData,
          cleanIgnoreDbsPatternsData,
          cleanTablesData,
          ignoreCleanTablesData,
          cleanDbData,
        ]) => ({
          ...clusterData,
          ...clearModeData,
          ...cleanDbsPatternsData,
          ...cleanIgnoreDbsPatternsData,
          ...cleanTablesData,
          ...ignoreCleanTablesData,
          ...cleanDbData,
        }),
      );
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
