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
    field="role"
    :label="t('扩容节点类型')"
    :min-width="150"
    required>
    <EditableSelect
      v-model="modelValue"
      :input-search="false"
      :list="renderList" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  interface Props {
    cluster: {
      spider_master: TendbClusterModel['spider_master'];
      spider_slave: TendbClusterModel['spider_slave'];
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const defaultOptions = [
    {
      label: 'Spider Master',
      value: 'spider_master',
    },
    {
      label: 'Spider Slave',
      value: 'spider_slave',
    },
  ];

  const renderList = computed(() =>
    defaultOptions.filter((item) => props.cluster[item.value as 'spider_master' | 'spider_slave'].length > 0),
  );

  watch(renderList, () => {
    if (!modelValue.value) {
      modelValue.value = renderList.value?.[0]?.value || '';
    }
  });
</script>
