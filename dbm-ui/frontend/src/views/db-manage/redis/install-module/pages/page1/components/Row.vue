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
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterTypeName"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.dbVersion"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderModule
        ref="moduleRef"
        :cluster-id="data.clusterId"
        :data="data.loadModules"
        :version="data.dbVersion" />
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
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/db-manage/redis/common/edit-field/ClusterName.vue';

  import { random } from '@utils';

  import RenderModule from './RenderModule.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    clusterId: number;
    bkCloudId: number;
    clusterType: string;
    clusterTypeName: string;
    dbVersion: string;
    loadModules: string[];
  }

  export interface InfoItem {
    bk_cloud_id: number;
    cluster_id: number;
    db_version: string;
    load_modules: string[];
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    clusterId: 0,
    bkCloudId: 0,
    clusterType: '',
    clusterTypeName: '',
    dbVersion: '',
    loadModules: [],
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputedClusters?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }
</script>
<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const moduleRef = ref<InstanceType<typeof RenderModule>>();

  const handleInputFinish = (value: RedisModel) => {
    emits('clusterInputFinish', value);
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
    moduleRef.value!.getValue().then((modules: string[]) => {
      emits('clone', {
        ...props.data,
        rowKey: random(),
        isLoading: false,
        loadModules: modules,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue(true);
      return await moduleRef.value!.getValue().then((modules: string[]) => ({
        bk_cloud_id: props.data.bkCloudId,
        cluster_id: props.data.clusterId,
        db_version: props.data.dbVersion,
        load_modules: modules,
      }));
    },
  });
</script>
