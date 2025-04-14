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
    :field="field"
    :label="label"
    :loading="loading"
    :min-width="minWidth"
    required>
    <EditableInput
      v-model="modelValue.ip"
      :placeholder="t('请输入n个主机IP', { n: limit })"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          v-bk-tooltips="t('从资源池选择')"
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableInput>
  </EditableColumn>
  <ResourceHostSelector
    v-model="selected"
    v-model:is-show="showSelector"
    :limit="limit"
    :params="params"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchList } from '@services/source/dbresourceResource';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface Props {
    field: string;
    label: string;
    minWidth?: number;
    params?: ComponentProps<typeof ResourceHostSelector>['params'];
  }

  withDefaults(defineProps<Props>(), {
    minWidth: 300,
    params: () => ({}),
  });

  /**
   * 绑定的modelValue须包含ip
   */
  const modelValue = defineModel<{
    bk_biz_id?: number;
    bk_cloud_id?: number;
    bk_host_id?: number;
    ip: string;
  }>({
    default: () => ({
      bk_biz_id: undefined,
      bk_cloud_id: undefined,
      bk_host_id: undefined,
      ip: '',
    }),
  });

  const { t } = useI18n();

  const limit = 1;
  const showSelector = ref(false);
  const selected = computed(() => (modelValue.value.bk_host_id ? ([modelValue.value] as IValue[]) : ([] as IValue[])));

  const rules = [
    {
      message: t('IP 格式不符合IPv4标准'),
      trigger: 'change',
      validator: (value: string) => ipv4.test(value),
    },
    {
      message: t('最多输入n个主机IP', { n: limit }),
      trigger: 'blur',
      validator: (value: string) => value.split(batchSplitRegex).length <= limit,
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

  const { loading, run: queryHost } = useRequest(fetchList, {
    manual: true,
    onSuccess: (data) => {
      const [currentHost] = data.results;
      if (currentHost) {
        modelValue.value.bk_biz_id = currentHost.dedicated_biz;
        modelValue.value.bk_cloud_id = currentHost.bk_cloud_id;
        modelValue.value.bk_host_id = currentHost.bk_host_id;
      }
    },
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      bk_biz_id: undefined,
      bk_cloud_id: undefined,
      bk_host_id: undefined,
      ip: value,
    };
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        hosts: value,
        limit,
        offset: 0,
      });
    }
  };

  const handleSelectorChange = (hostList: IValue[]) => {
    const [currentHost] = hostList;
    if (currentHost) {
      modelValue.value = {
        bk_biz_id: currentHost.dedicated_biz || currentHost.bk_biz_id,
        bk_cloud_id: currentHost.bk_cloud_id,
        bk_host_id: currentHost.bk_host_id,
        ip: currentHost.ip,
      };
    }
  };
</script>

<style lang="less" scoped>
  .select-icon {
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
