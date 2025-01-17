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
    :append-rules="editable ? rules : []"
    :field="field"
    :label="label"
    :loading="loading"
    :min-width="minWidth"
    required>
    <EditableInput
      v-if="editable"
      v-model="modelValue.ip"
      :placeholder="t('请选择主机')"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          v-bk-tooltips="t('从资源池选择')"
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableInput>
    <EditableBlock
      v-else
      v-model="modelValue.ip"
      :placeholder="t('请选择主机')">
      <template #append>
        <DbIcon
          v-bk-tooltips="t('从资源池选择')"
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableBlock>
  </EditableColumn>
  <ResourceHostSelector
    v-model="selected"
    v-model:is-show="showSelector"
    :need-num="1"
    :params="params"
    @change="handleSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchListDbaHost } from '@services/source/dbresourceResource';

  import { ipv4 } from '@common/regex';

  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface Props {
    field: string;
    label: string;
    minWidth?: number;
    editable?: boolean;
    params?: {
      for_biz?: number;
      bk_cloud_ids?: string;
      resource_type?: string;
      os_type?: string;
    };
  }

  withDefaults(defineProps<Props>(), {
    minWidth: 300,
    editable: false,
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
    default: () => ({}),
  });

  const { t } = useI18n();

  const showSelector = ref(false);
  const selected = computed(() => (modelValue.value.bk_host_id ? ([modelValue.value] as IValue[]) : ([] as IValue[])));

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
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        search_content: value,
        limit: -1,
        offset: 0,
      });
    }
  };

  const handleSelectorChange = (hostList: IValue[]) => {
    [modelValue.value] = hostList;
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
