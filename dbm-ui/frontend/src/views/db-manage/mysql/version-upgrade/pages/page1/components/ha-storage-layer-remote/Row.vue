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
      <RenderCluster
        ref="clusterRef"
        :model-value="clusterInfo"
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderOldMasterSlaveHost
        :data="oldMasterSlaveHost"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="readonlySlaveHost.join(',')"
        :is-loading="data.isLoading"
        :placeholder="readonlySlavePlaceholder">
        <template #content>
          <p
            v-for="item in readonlySlaveHost"
            :key="item">
            {{ item }}
          </p>
        </template>
      </RenderText>
    </td>
    <td style="padding: 0">
      <RenderCurrentVersion
        :charset="localCharset"
        :data="data.clusterData"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderTargetVersion
        ref="targetVersionRef"
        :data="data.clusterData"
        :is-loading="data.isLoading"
        :is-local="false"
        :target-module="data.targetModule"
        :target-package="data.targetPackage"
        :target-version="data.targetVersion"
        @module-change="handleModuleChange" />
    </td>
    <td style="padding: 0">
      <RenderMasterSlaveHost
        ref="masterSlaveHostRef"
        :cloud-id="data.clusterData?.cloudId"
        :disabled="!data.clusterData"
        :domain="data.clusterData?.domain"
        :master-host="data.masterHostData"
        :slave-host="data.slaveHostData" />
    </td>
    <td style="padding: 0">
      <RenderNewReadonlySlaveHost
        ref="newReadonlySlaveHostRef"
        :cloud-id="data.clusterData?.cloudId"
        :domain="data.clusterData?.domain"
        :ip-list="data.readonlyHostData"
        :slave-list="data.clusterData?.readonlySlaveList" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderCluster from '../RenderClusterWithRelateCluster.vue';
  import RenderCurrentVersion from '../RenderCurrentVersion.vue';

  import RenderMasterSlaveHost from './RenderMasterSlaveHost.vue';
  import RenderNewReadonlySlaveHost from './RenderNewReadonlySlaveHost.vue';
  import RenderOldMasterSlaveHost from './RenderOldMasterSlaveHost.vue';
  import RenderTargetVersion from './RenderTargetVersion.vue';

  export interface IHostData {
    bk_biz_id: number;
    bk_host_id: number;
    ip: string;
    bk_cloud_id: number;
  }

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterData?: {
      domain: string;
      clusterId: number;
      clusterType: string;
      currentVersion: string;
      packageVersion: string;
      moduleName: string;
      cloudId: number;
      masterSlaveList: IHostData[];
      readonlySlaveList: IHostData[];
    };
    targetVersion?: string;
    targetPackage?: number;
    targetModule?: number;
    masterHostData?: IHostData;
    slaveHostData?: IHostData;
    readonlyHostData?: IHostData[];
  }

  // 创建表格数据
  export const createRowData = (data?: Omit<IDataRow, 'rowKey' | 'isLoading'>): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ...data,
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: TendbhaModel | null): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }
</script>

<script setup lang="ts">
  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const targetVersionRef = ref<InstanceType<typeof RenderTargetVersion>>();
  const masterSlaveHostRef = ref<InstanceType<typeof RenderMasterSlaveHost>>();
  const newReadonlySlaveHostRef = ref<InstanceType<typeof RenderNewReadonlySlaveHost>>();
  const localCharset = ref('');

  const clusterInfo = computed(() => {
    if (props.data.clusterData) {
      return {
        id: props.data.clusterData.clusterId,
        domain: props.data.clusterData.domain,
      };
    }
    return undefined;
  });

  const oldMasterSlaveHost = computed(() => (props.data.clusterData?.masterSlaveList || []).map((item) => item.ip));
  const readonlySlaveHost = computed(() => (props.data.clusterData?.readonlySlaveList || []).map((item) => item.ip));

  const readonlySlavePlaceholder = computed(() => {
    if (!props.data.clusterData) {
      return t('选择集群后自动生成');
    }
    if (!props.data.clusterData.readonlySlaveList.length) {
      return t('无只读主机');
    }
    return '';
  });

  const handleClusterIdChange = (value: TendbhaModel | null) => {
    emits('clusterInputFinish', value);
  };

  const handleModuleChange = (value: string) => {
    localCharset.value = value;
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
    async getValue() {
      return await Promise.all([
        clusterRef.value!.getValue(),
        targetVersionRef.value!.getValue(),
        masterSlaveHostRef.value!.getValue(),
        newReadonlySlaveHostRef.value!.getValue(),
      ]).then((data) => {
        const [clusterData, targetVersionData, masterSlaveHostData, newReadonlySlaveHostData] = data;
        const clusterInfo = props.data.clusterData!;
        Object.assign(targetVersionData.display_info, {
          current_version: clusterInfo.currentVersion,
          current_package: clusterInfo.packageVersion,
          charset: localCharset.value,
          current_module_name: clusterInfo.moduleName,
          old_master_slave: oldMasterSlaveHost.value,
        });
        return {
          ...clusterData,
          ...targetVersionData,
          ...masterSlaveHostData,
          ...newReadonlySlaveHostData,
        };
      });
    },
  });
</script>
