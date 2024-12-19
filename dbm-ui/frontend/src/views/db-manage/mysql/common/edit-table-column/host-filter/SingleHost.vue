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
  <Column
    :append-rules="editable ? rules : []"
    :field="field"
    :label="label"
    :loading="loading"
    :min-width="300"
    required>
    <Input
      v-if="editable"
      v-model="modelValue.ip"
      :placeholder="t('请选择主机')"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </Input>
    <Block
      v-else
      v-model="modelValue.ip"
      :placeholder="t('请选择主机')">
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </Block>
  </Column>
  <ResourceHostSelector
    v-model:is-show="showSelector"
    :multiple="false"
    :params="params"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchListDbaHost } from '@services/source/dbresourceResource';

  import { ipv4 } from '@common/regex';

  import { Block, Column, Input } from '@components/editable-table/Index.vue';
  import ResourceHostSelector from '@components/resource-host-selector/Index.vue';

  type HostInfo = NonNullable<ComponentProps<typeof ResourceHostSelector>['modelValue']>[number];

  interface Props {
    field: string;
    label: string;
    editable?: boolean;
    params?: {
      for_biz?: number;
      bk_cloud_ids?: string;
      resource_type?: string;
      os_type?: string;
    };
  }

  withDefaults(defineProps<Props>(), {
    editable: false,
    params: () => ({}),
  });

  const modelValue = defineModel<Partial<HostInfo>>({
    default: () => ({}),
  });

  const { t } = useI18n();

  const showSelector = ref(false);

  const rules = [
    {
      validator: (value: string) => ipv4.test(value),
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
    },
    {
      validator: () => Boolean(modelValue.value.bk_host_id),
      message: t('目标主机不存在'),
      trigger: 'blur',
    },
  ];

  const { run: queryHost, loading } = useRequest(fetchListDbaHost, {
    manual: true,
    onSuccess: (data) => {
      console.log(data, 'data');
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    queryHost({
      search_content: value,
      limit: -1,
      offset: 0,
    });
  };

  const handleSelectorChange = (hostList: HostInfo[]) => {
    const [hostInfo] = hostList;
    modelValue.value = {
      bk_biz_id: hostInfo.dedicated_biz,
      bk_cloud_id: hostInfo.bk_cloud_id,
      bk_host_id: hostInfo.bk_host_id,
      ip: hostInfo.ip,
    };
  };
</script>

<style lang="less" scoped>
  :deep(.select-icon) {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
