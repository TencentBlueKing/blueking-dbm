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
        <RenderDbName
          ref="dbPatternsRef"
          :cluster-id="0"
          :model-value="data.dbPatterns"
          @change="handleDbPatternsChange" />
      </td>
      <td style="padding: 0">
        <RenderDbName
          ref="ignoreBackupDbsRef"
          :cluster-id="0"
          :model-value="data.ignoreBackupDbs"
          @change="handleIgnoreBackupDbsChange" />
      </td>
      <td style="padding: 0">
        <RenderDbs
          ref="backupDbsRef"
          :cluster-id-list="clusterIdList"
          :db-patterns="data.dbPatterns"
          :ignore-backup-dbs="data.ignoreBackupDbs"
          :model-value="data.backupDbs"
          @change="handleBackupOnChange" />
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
    rowKey?: string;
    dbPatterns: string[];
    backupDbs: string[];
    ignoreBackupDbs: string[];
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    dbPatterns: data.dbPatterns || [],
    backupDbs: data.backupDbs || [],
    ignoreBackupDbs: data.ignoreBackupDbs || [],
  });
</script>
<script setup lang="ts">
  import { ref } from 'vue';

  import RenderDbName from '@views/mysql/common/edit-field/DbName.vue';

  import RenderDbs from './RenderDbs.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterIdList: number[];
  }

  interface Emits {
    (e: 'add', params: IDataRow): void;
    (e: 'remove'): void;
    (e: 'change', value: IDataRow): void;
  }

  interface Exposes {
    getValue: () => Promise<any[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const dbPatternsRef = ref();
  const backupDbsRef = ref();
  const ignoreBackupDbsRef = ref();

  const dbPatterns = ref<string[]>([]);
  const backupDbs = ref<string[]>([]);
  const ignoreBackupDbs = ref<string[]>([]);

  const triggerChange = () => {
    emits('change', {
      rowKey: props.data.rowKey,
      dbPatterns: dbPatterns.value,
      backupDbs: backupDbs.value,
      ignoreBackupDbs: ignoreBackupDbs.value,
    });
  };

  const handleDbPatternsChange = (value: string[]) => {
    dbPatterns.value = value;
    triggerChange();
  };
  const handleIgnoreBackupDbsChange = (value: string[]) => {
    ignoreBackupDbs.value = value;
    triggerChange();
  };
  const handleBackupOnChange = (value: string[]) => {
    backupDbs.value = value;
    triggerChange();
  };

  const handleAppend = () => {
    emits('add', createRowData());
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
        dbPatternsRef.value.getValue('dbPatterns'),
        backupDbsRef.value.getValue('backupDbs'),
        ignoreBackupDbsRef.value.getValue('ignoreBackupDbs'),
      ]);
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
