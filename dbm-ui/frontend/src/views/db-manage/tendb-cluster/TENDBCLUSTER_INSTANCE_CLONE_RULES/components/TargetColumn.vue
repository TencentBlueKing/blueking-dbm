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
    :append-rules="rules"
    field="target"
    :label="t('新实例')"
    :loading="loading"
    :min-width="150"
    required>
    <Input
      v-model="modelValue"
      :placeholder="t('请输入IP_Port')"
      @change="handleInputChange" />
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import { ipPort } from '@common/regex';

  import { Column, Input } from '@components/editable-table/Index.vue';

  interface Props {
    tableData: {
      target: string;
    }[];
    source: {
      bk_cloud_id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const localValue = ref<{
    bk_host_id?: number;
    bk_cloud_id?: number;
    instance_address: string;
  }>({
    bk_host_id: undefined,
    bk_cloud_id: undefined,
    instance_address: '',
  });

  const rules = [
    {
      validator: (value: string) => ipPort.test(value),
      message: t('格式不符合要求'),
      trigger: 'change',
    },
    {
      validator: (value: string) => ipPort.test(value),
      message: t('格式不符合要求'),
      trigger: 'blur',
    },
    {
      validator: (value: string) => props.tableData.filter((item) => item.target === value).length < 2,
      message: t('新实例重复'),
      trigger: 'change',
    },
    {
      validator: (value: string) => props.tableData.filter((item) => item.target === value).length < 2,
      message: t('新实例重复'),
      trigger: 'blur',
    },
    {
      validator: () => Boolean(localValue.value.bk_host_id),
      message: t('新实例不存在'),
      trigger: 'blur',
    },
    {
      validator: () => localValue.value.bk_cloud_id === props.source.bk_cloud_id,
      message: t('新实例和源实例的管控区域不一致'),
      trigger: 'blur',
    },
  ];

  const { run: queryHost, loading } = useRequest(checkInstance, {
    manual: true,
    onSuccess: (data) => {
      if (data.length) {
        const [currentHost] = data;
        localValue.value = {
          bk_host_id: currentHost.bk_host_id,
          bk_cloud_id: currentHost.bk_cloud_id,
          instance_address: currentHost.instance_address,
        };
      }
    },
  });

  const handleInputChange = (value: string) => {
    localValue.value = {
      bk_host_id: undefined,
      bk_cloud_id: undefined,
      instance_address: '',
    };
    if (value) {
      queryHost({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        instance_addresses: [value],
      });
    }
  };
</script>
