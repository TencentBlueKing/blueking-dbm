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
    field="host.ip"
    fixed="left"
    :label="t('目标主机')"
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
    :label="t('关联实例')"
    :loading="loading"
    :min-width="150">
    <EditableBlock :placeholder="t('自动生成')">
      {{ modelValue.instance_address }}
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :label="t('实例角色')"
    :loading="loading"
    :min-width="150">
    <EditableBlock :placeholder="t('自动生成')">
      {{ modelValue.role }}
    </EditableBlock>
  </EditableColumn>
  <EditableColumn
    :label="t('关联集群')"
    :loading="loading"
    :min-width="150">
    <EditableBlock :placeholder="t('自动生成')">
      {{ modelValue.master_domain }}
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['SpiderHost']"
    hide-manual-input
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
    bk_cloud_id: number;
    bk_host_id: number;
    bk_idc_city_name: string;
    bk_sub_zone: string;
    cluster_id: number;
    instance_address: string;
    ip: string;
    master_domain: string;
    port: number;
    role: string;
    spec_id: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedHosts = computed<InstanceSelectorValues<IValue>>(() => ({
    SpiderHost: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as IValue,
    ),
  }));

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('主机不包含任何接入层实例'),
      trigger: 'blur',
      validator: (value: string) =>
        !value || modelValue.value.role === 'spider_master' || modelValue.value.role === 'spider_slave',
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data;
      if (item) {
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          bk_idc_city_name: item.host_info?.bk_idc_city_name || '',
          bk_sub_zone: item.host_info?.bk_sub_zone || '',
          cluster_id: item.cluster_id,
          instance_address: item.instance_address,
          ip: item.ip,
          master_domain: item.master_domain,
          port: item.port,
          role: item.role,
          spec_id: item.spec_config.id,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.SpiderHost);
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: 0,
      bk_idc_city_name: '',
      bk_sub_zone: '',
      cluster_id: 0,
      instance_address: '',
      ip: value,
      master_domain: '',
      port: 0,
      role: '',
      spec_id: 0,
    };
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
