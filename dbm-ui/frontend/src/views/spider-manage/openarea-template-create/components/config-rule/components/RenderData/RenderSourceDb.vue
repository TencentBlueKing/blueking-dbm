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
  <BkLoading :loading="isLoading">
    <TableEditSelect
      ref="editRef"
      v-model="modelValue"
      :disabled="!clusterId"
      :list="dbNameList"
      :placeholder="t('请选择')"
      :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getClusterDatabaseNameList,
  } from '@services/source/remoteService';

  import TableEditSelect from '@components/tools-table-select/index.vue';

  interface Props {
    clusterId: number,
  }

  interface Exposes {
    getValue: () => Promise<{
      source_db: string
    }>
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: false,
    default: '',
  });

  const { t } = useI18n();

  const editRef = ref<InstanceType<typeof TableEditSelect>>();
  const dbNameList = shallowRef<{value: string, label: string}[]>([]);

  const rules = [
    {
      validator: (value: string[]) => value.length > 0,
      message: t('克隆 DB 不能为空'),
    },
  ];

  const {
    loading: isLoading,
    run: fetchList,
  } = useRequest(getClusterDatabaseNameList, {
    manual: true,
    onSuccess(data) {
      const [{
        databases,
      }] = data;

      dbNameList.value = databases.map(item => ({
        value: item,
        label: item,
      }));
    },
  });

  watch(() => props.clusterId, () => {
    if (props.clusterId) {
      fetchList({
        cluster_ids: [props.clusterId],
      });
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return (editRef.value as InstanceType<typeof TableEditSelect>)
        .getValue()
        .then(() => ({
          source_db: modelValue.value,
        }));
    },
  });
</script>
