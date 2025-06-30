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
    field="master.instance_address"
    fixed="left"
    label="Master"
    :loading="loading"
    :min-width="150"
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
      :placeholder="t('请输入如: 192.168.10.2:1000')"
      @change="handleChange" />
  </EditableColumn>
  <InstanceResourceSelector
    v-model:is-show="showSelector"
    v-model:selected="dataList"
    :cluster-type="ClusterTypes.TENDBCLUSTER"
    role="remote_master"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getGlobalInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceResourceSelector, { type IInstance } from '@components/instance-resource-selector/Index.vue';

  export type IValue = IInstance;

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_id: number;
    instance_address: string;
    ip: string;
    master_domain: string;
    port: number;
    role: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const dataList = shallowRef<IValue[]>([]);

  const rules = [
    {
      message: t('目标实例输入格式有误'),
      trigger: 'blur',
      validator: (value: string) => !value || ipPort.test(value),
    },
    {
      message: t('目标实例不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('非主库实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'remote_master',
    },
  ];

  const { loading, run: queryInstance } = useRequest(getGlobalInstance, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data.results;
      if (item) {
        modelValue.value = {
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_id: item.cluster_id,
          instance_address: item.instance_address,
          ip: item.ip,
          master_domain: item.master_domain,
          port: item.port,
          role: item.role,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: 0,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      instance_address: value,
      ip: '',
      master_domain: '',
      port: 0,
      role: '',
    };
  };

  const handleSelectorChange = (selected: IValue[]) => {
    emits('batch-edit', selected);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.instance_address && !modelValue.value.bk_host_id) {
        queryInstance({
          cluster_type: ClusterTypes.TENDBCLUSTER,
          db_type: DBTypes.TENDBCLUSTER,
          instance_address: modelValue.value.instance_address,
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
