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
    field="slave.ip"
    fixed="left"
    :label="t('目标从库主机')"
    :loading="loading"
    :min-width="220"
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
    field="slave.related_clusters"
    :label="t('同机关联集群')"
    :loading="loading"
    :min-width="220"
    required>
    <EditableBlock :placeholder="t('自动生成')">
      <p
        v-for="item in modelValue.related_clusters"
        :key="item.id">
        {{ item.master_domain }}
      </p>
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['TendbhaHost']"
    hide-manual-input
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

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
    bk_idc_city_name: string;
    bk_sub_zone: string;
    ip: string;
    related_clusters: {
      id: number;
      master_domain: string;
    }[];
    role: string;
    spec_id: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    TendbhaHost: [
      {
        id: 'TendbhaHost',
        name: t('目标从库主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Slave 主机'),
            role: 'backend_slave',
          },
        },
        topoConfig: {
          countFunc: (cluster: TendbhaModel) => {
            return cluster.slaves.length;
          },
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Slave 主机'),
            role: 'backend_slave',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const showSelector = ref(false);
  const selectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    TendbhaHost: props.selected.map(
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
        !value || illegalInstances ? t('主机包含非 Slave 实例 (instances)', [illegalInstances]) : true,
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      illegalInstances = data
        .filter((item) => item.role !== 'backend_slave')
        .map((item) => item.instance_address)
        .join('、');
      const [currentHost] = data;
      if (currentHost) {
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          bk_idc_city_name: currentHost.host_info?.bk_idc_city_name || '',
          bk_sub_zone: currentHost.host_info?.bk_sub_zone || '',
          ip: currentHost.ip,
          related_clusters: currentHost.related_clusters.map((item) => ({
            id: item.id,
            master_domain: item.master_domain,
          })),
          role: currentHost.role,
          spec_id: currentHost.spec_config.id,
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
      bk_idc_city_name: '',
      bk_sub_zone: '',
      ip: value,
      related_clusters: [],
      role: '',
      spec_id: 0,
    };
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.TendbhaHost);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBHA],
          db_type: DBTypes.MYSQL,
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
