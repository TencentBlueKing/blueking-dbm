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
    field="instance.instance_address"
    fixed="left"
    id-mark="ins"
    :label="t('目标实例')"
    :loading="loading"
    :min-width="350"
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
      @change="handleInputChange" />
  </EditableColumn>
  <InstanceSelector
    v-model="selectedInstances"
    v-model:is-show="showSelector"
    :cluster-types="[ClusterTypes.REDIS]"
    :data-source-map="dataSourceMap"
    @change="handleInstanceSelectChange" />
</template>
<script lang="ts" setup>
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { checkInstance } from '@services/source/dbbase';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';
  import { ipPort } from '@common/regex';

  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  interface Props {
    dataSourceMap?: ComponentProps<typeof InstanceSelector>['dataSourceMap'];
    selected: {
      instance_address: string;
    }[];
  }

  type Emits = (e: 'batch-edit', list: RedisInstanceModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_id: number;
    cluster_type: string;
    cluster_type_name: string;
    instance_address: string;
    master_domain: string;
  }>({
    default: () => ({
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      cluster_type: '',
      cluster_type_name: '',
      instance_address: '',
      master_domain: '',
    }),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selectedInstances = computed(() => ({
    [ClusterTypes.REDIS]: props.selected.map((item) => ({
      instance_address: item.instance_address,
    })) as RedisInstanceModel[],
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
  ];

  const { loading, run: queryHost } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data;
      if (currentHost) {
        modelValue.value = {
          bk_cloud_id: currentHost.bk_cloud_id,
          bk_host_id: currentHost.bk_host_id,
          cluster_id: currentHost.cluster_id,
          cluster_type: currentHost.cluster_type,
          cluster_type_name: clusterTypeInfos[currentHost.cluster_type as ClusterTypes].name,
          instance_address: currentHost.instance_address,
          master_domain: currentHost.master_domain,
        };
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_id: 0,
      cluster_type: '',
      cluster_type_name: '',
      instance_address: value,
      master_domain: '',
    };
  };

  const handleInstanceSelectChange = (selected: { [ClusterTypes.REDIS]: RedisInstanceModel[] }) => {
    emits(
      'batch-edit',
      Object.values(selected).flatMap((item) => item),
    );
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.instance_address && !modelValue.value.bk_host_id) {
        queryHost({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          db_type: DBTypes.REDIS,
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
