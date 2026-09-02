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
      v-model.trim="modelValue.ip"
      :placeholder="t('请输入IP')"
      @change="handleInputChange" />
  </EditableColumn>
  <EditableColumn
    field="host.related_instances"
    :label="t('关联集群实例')"
    :loading="loading"
    :min-width="220"
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
  <HostSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.TENDBSINGLE]"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { checkInstance } from '@services/source/dbbase';

  import { ClusterTypes, DBTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import HostSelector, { type HostModel, type HostSelectorValues } from '@components/host-selector/Index.vue';

  export type SelectorHost = HostModel<ClusterTypes.TENDBSINGLE>;

  interface Props {
    selected: {
      ip: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: SelectorHost[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    city: string;
    ip: string;
    related_instances: ServiceReturnType<typeof checkInstance>;
    spec: TendbsingleModel['masters'][0]['spec_config'];
    subzones: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedInstances = computed<HostSelectorValues<ClusterTypes.TENDBSINGLE>>(() => ({
    [ClusterTypes.TENDBSINGLE]: props.selected.map(
      (item) =>
        ({
          ip: item.ip,
        }) as HostModel<ClusterTypes.TENDBSINGLE>,
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
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const relatedInstances = data;
      const [currentHost] = data;
      if (currentHost) {
        const [{ region, zone_names: zoneNames }] = currentHost.related_clusters;
        modelValue.value = {
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          city: region && region !== 'default' ? region : '',
          ip: currentHost.ip,
          related_instances: relatedInstances,
          spec: currentHost.spec_config,
          subzones: zoneNames?.join(',') || '',
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = Object.assign({} as typeof modelValue.value, {
      bk_cloud_id: 0,
      bk_host_id: 0,
      city: '',
      ip: value,
      related_instances: [],
      spec: {
        id: 0,
      },
      subzones: '',
    });
  };

  const handleSelectorChange = (selected: HostSelectorValues<ClusterTypes.TENDBSINGLE>) => {
    emits('batch-edit', selected[ClusterTypes.TENDBSINGLE]);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.ip && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type: [ClusterTypes.TENDBSINGLE],
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
