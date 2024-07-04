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
  <tr>
    <td style="padding: 0">
      <RenderDomain
        ref="domainRef"
        :data="data.domain"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="backupDbsRef"
        :cluster-id="data.clusterId"
        :model-value="data.backupDbs"
        required
        @change="handleBackupDbsChange" />
    </td>
    <td style="padding: 0">
      <RenderDbName
        ref="ignoreDbsRef"
        :cluster-id="data.clusterId"
        :model-value="data.ignoreDbs"
        @change="handleIgnoreDbsChange" />
    </td>
    <td style="padding: 0">
      <div v-if="finalDbs?.length">
        <BkButton
          class="pl-16"
          text
          theme="primary"
          @click="handleFinalDbsCountClick">
          {{ finalDbs.length }}
        </BkButton>
      </div>
      <div
        v-else
        v-bk-tooltips="t('请先设置 备份/忽略 DB')"
        class="final-dbs-placeholder">
        {{ t('自动生成') }}
      </div>
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver'

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import { random } from '@utils';

  import RenderDbName from './RenderDbName.vue';
  import RenderDomain from './RenderDomain.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    domain: string;
    clusterId: number;
    clusterType: string;
    backupDbs: string[];
    ignoreDbs: string[];
  }

  // 创建表格数据
  export const createRowData = (params?: {
    domain: string;
    clusterId: number;
    clusterType: string;
    backupDbs: string[];
    ignoreDbs: string[];
  }): IDataRow =>
    Object.assign(
      {
        rowKey: random(),
        isLoading: false,
        domain: '',
        clusterId: 0,
        clusterType: '',
        backupDbs: [],
        ignoreDbs: [],
      },
      params,
    );
</script>

<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add'): void;
    (e: 'remove'): void;
    (e: 'inputClusterFinish', value: string): void;
    (e: 'showFinalReviewer'): void;
    (e: 'inputBackupDbsFinish', value: string[]): void;
    (e: 'inputIgnoreDbsFinish', value: string[]): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_id: number;
      backup_dbs: string[]
    }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const domainRef = ref<InstanceType<typeof RenderDomain>>();
  const backupDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const ignoreDbsRef = ref<InstanceType<typeof RenderDbName>>();
  const backupDbs = ref(props.data.backupDbs);
  const ignoreDbs = ref(props.data.ignoreDbs);

  const {
    data: finalDbs,
    run: getSqlserverDbsRun
  } = useRequest(getSqlserverDbs, {
    manual: true,
  })

  const getFinalDbsNew = (backupDbs: string[], ignoreDbs: string[]) => {
    getSqlserverDbsRun({
      cluster_id: props.data.clusterId,
      db_list: backupDbs,
      ignore_db_list: ignoreDbs
    })
  }

  const handleInputFinish = (domain: string) => {
    emits('inputClusterFinish', domain);
  };

  const handleBackupDbsChange = (value: string[]) => {
    backupDbs.value = value;
    getFinalDbsNew(value, ignoreDbs.value)
    emits('inputBackupDbsFinish', value);
  };

  const handleIgnoreDbsChange = (value: string[]) => {
    ignoreDbs.value = value;
    getFinalDbsNew(backupDbs.value, value)
    emits('inputIgnoreDbsFinish', value);
  };

  const handleFinalDbsCountClick = () => {
    emits('showFinalReviewer');
  };

  const handleAppend = () => {
    emits('add');
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
        domainRef.value!.getValue(),
        backupDbsRef.value!.getValue(),
        ignoreDbsRef.value!.getValue(),
      ]).then(([clusterId]) => ({
        cluster_id: clusterId,
        backup_dbs: finalDbs?.value || []
      }));
    },
  });
</script>

<style lang="less" scoped>
  .final-dbs-placeholder {
    padding-left: 16px;
    color: #c4c6cc;
  }
</style>
