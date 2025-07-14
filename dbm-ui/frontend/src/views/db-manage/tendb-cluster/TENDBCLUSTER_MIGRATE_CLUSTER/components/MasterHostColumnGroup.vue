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
    field="oldMaster.ip"
    fixed="left"
    :label="t('目标主库主机')"
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
      v-model="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleInputChange" />
  </EditableColumn>
  <EditableColumn
    :label="t('主库主机关联实例')"
    :loading="loading"
    :min-width="150">
    <EditableBlock :placeholder="t('自动生成')">
      <p
        v-for="item in modelValue.related_instances"
        :key="item">
        {{ item }}
      </p>
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['TendbClusterHost']"
    :selected="selectedHosts"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';

  export type SelectorHost = IValue;

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_id: number;
    ip: string;
    master_domain: string;
    related_instances: string[];
    role: string;
    spec_id: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedHosts = computed<InstanceSelectorValues<IValue>>(() => ({
    TendbClusterHost: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as IValue,
    ),
  }));
  let illegalInstances = '';

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'change',
      validator: (value: string) => !value || props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) =>
        !value || illegalInstances ? t('主机包含非 Master 实例 (instances)', [illegalInstances]) : true,
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      illegalInstances = data
        .filter((item) => item.role !== 'remote_master')
        .map((item) => item.instance_address)
        .join('、');
      const [item] = data;
      if (item) {
        const relatedInstances: string[] = [];
        data.forEach((item) => {
          relatedInstances.push(item.instance_address);
        });
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          cluster_id: item.cluster_id,
          ip: item.ip,
          master_domain: item.master_domain,
          related_instances: relatedInstances,
          role: item.role,
          spec_id: item.spec_config?.id || -1,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    illegalInstances = '';
    modelValue.value = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      ip: value,
      master_domain: '',
      related_instances: [],
      role: '',
      spec_id: 0,
    };
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.TendbClusterHost);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBCLUSTER],
          db_type: DBTypes.TENDBCLUSTER,
          instance_addresses: [modelValue.value.ip],
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
