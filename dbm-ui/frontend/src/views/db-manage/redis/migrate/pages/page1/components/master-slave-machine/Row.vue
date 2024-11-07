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
    <FixedColumn fixed="left">
      <RenderHost
        ref="hostRef"
        :data="data.clusterData?.ip"
        :inputed="inputedIps"
        @input-finish="handleInputFinish" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderOldMasterSlaveHost
        ref="instanceRef"
        :data="data.clusterData?.relatedInstance"
        :is-loading="data.isLoading"
        :placeholder="t('自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderSpec
        ref="specRef"
        :current-spec-id="data.clusterData?.currentSpecId"
        :data="data.clusterData"
        :is-loading="data.isLoading"
        :selected-spec-id="localSpec" />
    </td>
    <td style="padding: 0">
      <RenderTargetClusterVersion
        ref="versionRef"
        :cluster-type="data.clusterData?.clusterType"
        :data="localVersion"
        :is-loading="data.isLoading" />
    </td>
    <OperateColumn
      :removeable="removeable"
      show-clone
      @add="handleAppend"
      @clone="handleClone"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import type { ComponentExposed, ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderHost from '@views/db-manage/redis/common/edit-field/HostName.vue';
  import RenderTargetClusterVersion from '@views/db-manage/redis/common/edit-field/VersionSelect.vue';

  import { random } from '@utils';

  import RenderSpec from '../common/render-spec/Index.vue';
  import RenderOldMasterSlaveHost from '../common/RenderOldMasterSlaveHost.vue';

  export interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterData?: {
      ip: string;
      cloudId: number;
      clusterType: string;
      // related_cluster: RedisMachineModel['related_clusters'];
      relatedInstance: ComponentProps<typeof RenderOldMasterSlaveHost>['data'];
      currentSpecId: number;
      dbVersion: string;
    };
    targetSpecId?: number;
    targetVersion?: string;
  }

  export type IDataRowBatchKey = keyof Pick<IDataRow, 'targetSpecId' | 'targetVersion'>;

  // 创建表格数据
  export const createRowData = (data?: Omit<IDataRow, 'rowKey' | 'isLoading'>): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ...data,
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputedIps?: string[];
  }

  interface Emits {
    (e: 'add', params: IDataRow[]): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'ipInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      instance: Awaited<ReturnType<ComponentExposed<typeof RenderOldMasterSlaveHost>['getValue']>>;
      resource_spec: {
        backend_group: {
          spec_id: string;
          count: number;
        };
      };
      db_version: string;
      display_info: {
        migrate_type: 'machine';
        ip: string;
        domain: string;
      };
    }>;
  }
</script>

<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    inputedIps: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const hostRef = ref<InstanceType<typeof RenderHost>>();
  const instanceRef = ref<InstanceType<typeof RenderOldMasterSlaveHost>>();
  const specRef = ref<InstanceType<typeof RenderSpec>>();
  const versionRef = ref<InstanceType<typeof RenderTargetClusterVersion>>();

  const localSpec = computed(() => {
    if (props.data.targetSpecId) {
      return props.data.targetSpecId;
    }
    return props.data.clusterData?.currentSpecId;
  });

  const localVersion = computed(() => {
    if (props.data.targetVersion) {
      return props.data.targetVersion;
    }
    return props.data.clusterData?.dbVersion;
  });

  const handleInputFinish = (value: string) => {
    emits('ipInputFinish', value.split(':')[1]);
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

  const handleClone = () => {
    Promise.allSettled([
      hostRef.value!.getValue(true),
      instanceRef.value!.getValue(),
      specRef.value!.getValue(),
      versionRef.value!.getValue(),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          clusterData: props.data.clusterData,
          targetSpecId: rowInfo[2],
          targetVersion: rowInfo[3],
        }),
      );
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all([
        hostRef.value!.getValue(true),
        instanceRef.value!.getValue(),
        specRef.value!.getValue(),
        versionRef.value!.getValue(),
      ]).then((data) => {
        const [hostData, instanceData, specData, versionData] = data;
        return {
          instance: instanceData,
          resource_spec: {
            backend_group: {
              spec_id: specData,
              count: 1,
            },
          },
          db_version: versionData,
          display_info: {
            migrate_type: 'machine',
            ip: hostData,
            domain: '',
          },
        };
      });
    },
  });
</script>
