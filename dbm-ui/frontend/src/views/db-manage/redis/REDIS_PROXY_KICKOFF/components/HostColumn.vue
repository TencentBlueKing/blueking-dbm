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
    field="proxy.ip"
    fixed="left"
    :label="t('Proxy 主机')"
    :loading="loading"
    :min-width="240"
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
      :placeholder="t('请输入 Proxy 主机')"
      @change="handleChange" />
  </EditableColumn>
  <HostSelector
    v-model="selectedHosts"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :data-source-map="dataSourceMap"
    :tab-name-map="{ [ClusterTypes.REDIS]: t('Proxy 主机') }"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getGlobalMachine } from '@services/source/dbbase';
  import { getRedisMachineList } from '@services/source/redis';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, { type HostModel, type HostSelectorValues } from '@components/host-selector/Index.vue';

  export type SelectorHost = HostModel<ClusterTypes.REDIS>;

  interface Props {
    selected: {
      bk_biz_id?: number;
      bk_cloud_id?: number;
      bk_host_id?: number;
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SelectorHost[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    bk_sub_zone: string;
    city_name: string;
    cluster_id: number;
    cluster_type: string;
    ip: string;
    master_domain: string;
    role: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  // Proxy 主机：角色过滤 proxy
  const dataSourceMap = {
    [ClusterTypes.REDIS]: (params: ServiceParameters<typeof getRedisMachineList>) =>
      getRedisMachineList({
        ...params,
        instance_role: 'proxy',
      }),
  };

  const showSelector = ref(false);
  const selectedHosts = computed<HostSelectorValues<ClusterTypes.REDIS>>(() => ({
    [ClusterTypes.REDIS]: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as HostModel<ClusterTypes.REDIS>,
    ),
  }));

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
      message: t('主机不包含任何 Proxy 实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'proxy',
    },
  ];

  const { loading, run: queryMachine } = useRequest(getGlobalMachine, {
    manual: true,
    onSuccess: (data) => {
      const [item] = data.results;
      if (item) {
        modelValue.value = {
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          bk_sub_zone: item.host_info.bk_sub_zone,
          city_name: item.host_info.bk_idc_city_name,
          cluster_id: item.related_clusters[0].id,
          cluster_type: item.cluster_type,
          ip: item.ip,
          master_domain: item.related_clusters[0].immute_domain,
          role: item.instance_role,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: 0,
      bk_sub_zone: '',
      city_name: '',
      cluster_id: 0,
      cluster_type: '',
      ip: value,
      master_domain: '',
      role: '',
    };
  };

  const handleSelectorChange = (selected: HostSelectorValues<ClusterTypes.REDIS>) => {
    emits('batch-edit', selected[ClusterTypes.REDIS]);
  };

  watch(
    modelValue,
    () => {
      if (!modelValue.value.bk_host_id && modelValue.value.ip) {
        queryMachine({
          db_type: DBTypes.REDIS,
          ip: modelValue.value.ip,
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
