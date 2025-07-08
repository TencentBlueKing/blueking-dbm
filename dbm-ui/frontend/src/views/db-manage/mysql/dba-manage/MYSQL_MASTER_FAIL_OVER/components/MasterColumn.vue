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
    field="master.ip"
    fixed="left"
    :label="t('故障主库主机')"
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
      :placeholder="t('请输入如: 192.168.10.2')"
      @change="handleChange" />
  </EditableColumn>
  <MachineResourceSelector
    v-model:is-show="showSelector"
    v-model:selected="dataList"
    :cluster-types="[ClusterTypes.TENDBHA]"
    role="backend_master"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getGlobalMachine } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import MachineResourceSelector, { type IMachine } from '@components/machine-resource-selector/Index.vue';

  export type IValue = IMachine;

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
    related_clusters: {
      id: number;
      master_domain: string;
    }[];
    role: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const dataList = shallowRef<IValue[]>([]);

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'blur',
      validator: (value: string) => !value || ipv4.test(value),
    },
    {
      message: t('目标主机不存在'),
      trigger: 'blur',
      validator: (value: string) => !value || Boolean(modelValue.value.bk_host_id),
    },
    {
      message: t('非 Master IP'),
      trigger: 'blur',
      validator: (value: string) => !value || modelValue.value.role === 'backend_master',
    },
  ];

  const { loading, run: queryMachine } = useRequest(getGlobalMachine, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data.results;
      if (currentHost) {
        modelValue.value = {
          bk_biz_id: currentHost.bk_biz_id,
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          ip: currentHost.ip,
          related_clusters: currentHost.related_clusters.map((item) => ({
            id: item.id,
            master_domain: item.immute_domain,
          })),
          role: currentHost.instance_role,
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
      ip: value,
      related_clusters: [],
      role: '',
    };
  };

  const handleSelectorChange = (selected: IValue[]) => {
    emits('batch-edit', selected);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryMachine({
          cluster_type: ClusterTypes.TENDBHA,
          db_type: DBTypes.MYSQL,
          instance_role: 'backend_master',
          ip: modelValue.value.ip,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.selected,
    () => {
      dataList.value = props.selected.map(
        (item) =>
          ({
            bk_biz_id: item.bk_biz_id,
            instance_role: item.role,
            ip: item.ip,
          }) as IValue,
      );
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
