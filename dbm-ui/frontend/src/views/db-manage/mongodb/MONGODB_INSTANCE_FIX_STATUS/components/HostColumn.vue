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
    field="host.ip"
    fixed="left"
    :label="t('目标主机')"
    :loading="loading"
    :min-width="150"
    required
    :rules="rules">
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
      :placeholder="t('请输入如: 192.168.10.2')"
      @change="handleChange" />
  </EditableColumn>
  <EditableColumn
    :label="t('关联实例')"
    :loading="loading"
    :min-width="150"
    readonly>
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-for="item in modelValue.related_instances"
        :key="item.instance_address">
        <p>
          {{ item.master_domain }}
        </p>
        <p style="color: #979ba5">--{{ item.instance_address }}</p>
      </div>
    </EditableBlock>
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['mongoCluster']"
    hide-manual-input
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { checkInstance } from '@services/source/dbbase';
  import { getMongoInstancesList, getMongoTopoList } from '@services/source/mongodb';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  export type SelectorHost = IValue;

  interface Props {
    selected: Array<typeof modelValue.value>;
  }

  type Emits = (e: 'batch-edit', list: IValue[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
    related_instances: ServiceReturnType<typeof checkInstance>;
    role: string;
    spec_config: Record<string, any>;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    mongoCluster: [
      {
        id: 'mongoCluster',
        name: t('目标主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: t('目标主机'),
          },
          getTableList: (params: ServiceParameters<typeof getMongoInstancesList>) =>
            getMongoInstancesList(
              Object.assign({}, params, {
                cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
                role: 'proxy',
              }),
            ),
          multiple: true,
        },
        topoConfig: {
          countFunc: (data: MongodbModel) => data.mongos.length,
          getTopoList: (params: ServiceParameters<typeof getMongoTopoList>) =>
            getMongoTopoList(
              Object.assign({}, params, {
                cluster_type: ClusterTypes.MONGO_SHARED_CLUSTER,
              }),
            ),
        },
      },
    ],
  } as Record<string, PanelListType>;

  const showSelector = ref(false);
  const selectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    mongoCluster: props.selected.map(
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
      message: t('主机不包含任何 Mongos 实例'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'proxy',
    },
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const relatedInstances = data;
        const [hostInfo] = data;
        modelValue.value = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: hostInfo.bk_cloud_id,
          bk_host_id: hostInfo.bk_host_id,
          ip: hostInfo.ip,
          port: hostInfo.port || 0,
          related_instances: relatedInstances,
          role: hostInfo.role,
          spec_config: hostInfo.spec_config || {},
        };
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
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: value,
        port: 0,
        related_instances: [],
        role: '',
        spec_config: {},
      },
    );
  };

  const handleSelectorChange = (selected: InstanceSelectorValues<IValue>) => {
    emits('batch-edit', selected.mongoCluster);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.MONGO_SHARED_CLUSTER],
          db_type: DBTypes.MONGODB,
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
