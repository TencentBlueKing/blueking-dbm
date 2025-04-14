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
    :label="t('从库主机关联实例')"
    :loading="loading"
    :min-width="150">
    <EditableBlock v-if="modelValue.related_instances.length">
      <p
        v-for="item in modelValue.related_instances"
        :key="item">
        {{ item }}
      </p>
    </EditableBlock>
    <EditableBlock
      v-else
      :placeholder="t('自动生成')" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['TendbClusterHost']"
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import type { ClusterTypes } from '@common/const';
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
    bk_host_id?: number;
    cluster_id: number;
    ip: string;
    master_domain: string;
    related_instances: string[];
    spec_id: number;
    spec_name: string;
  }>({
    default: () => ({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: undefined,
      cluster_id: 0,
      ip: '',
      master_domain: '',
      related_instances: [],
      spec_id: 0,
      spec_name: '',
    }),
  });

  const { t } = useI18n();

  const tabListConfig = {
    TendbClusterHost: [
      {
        name: t('目标从库'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Slave 主机'),
            role: 'remote_slave',
          },
        },
      },
      {
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('Slave 主机'),
            role: 'remote_slave',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const showSelector = ref(false);
  const selectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    TendbClusterHost: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as IValue,
    ),
  }));

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('目标主机重复'),
      trigger: 'blur',
      validator: (value: string) => props.selected.filter((item) => item.ip === value).length < 2,
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return Boolean(modelValue.value.bk_host_id);
      },
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [currentHost] = data;
        const relatedInstances: string[] = [];
        data.forEach((item) => {
          relatedInstances.push(item.instance_address);
        });
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          cluster_id: currentHost.cluster_id,
          ip: currentHost.ip,
          master_domain: currentHost.master_domain,
          related_instances: relatedInstances,
          spec_id: currentHost.spec_config.id,
          spec_name: currentHost.spec_config.name,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: undefined,
      cluster_id: 0,
      ip: value,
      master_domain: '',
      related_instances: [],
      spec_id: 0,
      spec_name: '',
    };
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        instance_addresses: [value],
      });
    }
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.TendbClusterHost);
  };

  watch(
    () => modelValue.value.ip,
    () => {
      handleInputChange(modelValue.value.ip);
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
