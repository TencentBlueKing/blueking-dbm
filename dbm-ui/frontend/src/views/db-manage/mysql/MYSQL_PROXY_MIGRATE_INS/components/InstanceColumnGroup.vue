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
  <EditableColumn
    :append-rules="rules"
    field="originProxy.instance_address"
    fixed="left"
    :label="t('目标Proxy实例')"
    :loading="loading"
    :min-width="200"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableInput
      v-model="modelValue.instance_address"
      :placeholder="t('请输入IP:Port')"
      @change="handleChange" />
  </EditableColumn>
  <EditableColumn
    :label="t('关联集群')"
    :loading="loading"
    :min-width="240"
    readonly
    :rowspan="rowspan">
    <EditableBlock
      v-model="modelValue.master_domain"
      :placeholder="t('自动生成')" />
  </EditableColumn>
  <InstanceSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBHA]"
    :data-source-map="dataSourceMap"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { checkInstance } from '@services/source/dbbase';
  import { getTendbhaInstanceList } from '@services/source/tendbha';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  interface Props {
    handleRowMerge: () => void;
    rowspan: number;
    selected: Array<typeof modelValue.value>;
  }

  type Emits = (e: 'batch-edit', list: TendbhaInstanceModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    city: string;
    cluster_id: number;
    instance_address: string;
    ip: string;
    master_domain: string;
    port: number;
    role: string;
    spec_config: TendbhaModel['masters'][number]['spec_config'];
    subzones: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const dataSourceMap = {
    [ClusterTypes.TENDBHA]: (params: ServiceParameters<typeof getTendbhaInstanceList>) =>
      getTendbhaInstanceList({
        ...params,
        role: 'proxy',
      }),
  };

  const showSelector = ref(false);
  const selectedInstances = computed(() => ({
    [ClusterTypes.TENDBHA]: props.selected.map((item) => ({
      instance_address: item.instance_address,
    })) as TendbhaInstanceModel[],
  }));

  const rules = [
    {
      message: t('实例格式有误，请输入 IP:Port'),
      trigger: 'change',
      validator: (value: string) => !value || ipPort.test(value),
    },
    {
      message: t('目标实例重复'),
      trigger: 'change',
      validator: (value: string) =>
        !value || props.selected.filter((item) => item.instance_address === value).length < 2,
    },
    {
      message: t('目标实例不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('该实例为非 Proxy 实例，请选择 Proxy 实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'proxy',
    },
  ];

  const { loading, run: queryInstance } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [instanceInfo] = data;
        const [{ region, zone_names: zoneNames }] = instanceInfo.related_clusters;
        modelValue.value = {
          bk_cloud_id: instanceInfo.bk_cloud_id,
          bk_host_id: instanceInfo.bk_host_id,
          city: region && region !== 'default' ? region : '',
          cluster_id: instanceInfo.cluster_id,
          instance_address: instanceInfo.instance_address,
          ip: instanceInfo.ip,
          master_domain: instanceInfo.master_domain,
          port: instanceInfo.port,
          role: instanceInfo.role,
          spec_config: instanceInfo.spec_config,
          subzones: zoneNames?.join(',') || '',
        };
        setTimeout(() => {
          props.handleRowMerge();
        });
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = Object.assign(
      {},
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        city: '',
        cluster_id: 0,
        instance_address: value,
        ip: '',
        master_domain: '',
        port: 0,
        role: '',
        spec_config: {} as TendbhaModel['masters'][number]['spec_config'],
        subzones: '',
      },
    );
  };

  const handleSelectorChange = (selected: { [ClusterTypes.TENDBHA]: TendbhaInstanceModel[] }) => {
    emits(
      'batch-edit',
      Object.values(selected).flatMap((item) => item),
    );
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.instance_address && !modelValue.value.bk_host_id) {
        queryInstance({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA],
          db_type: DBTypes.MYSQL,
          instance_addresses: [modelValue.value.instance_address],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
