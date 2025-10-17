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
    :disabled-method="disabledMethod"
    field="source_db"
    :label="t('克隆 DB')"
    :loading="loading"
    :min-width="200"
    required>
    <EditableSelect
      v-model="modelValue"
      :list="dbNameList">
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterDatabaseNameList } from '@services/source/remoteService';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const dbNameList = shallowRef<{ label: string; value: string }[]>([]);

  const { loading, run: fetchList } = useRequest(getClusterDatabaseNameList, {
    manual: true,
    onSuccess(data) {
      const [{ databases }] = data;
      dbNameList.value = databases.map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  const disabledMethod = () => {
    if (!props.clusterId) {
      return t('请先选择集群');
    }
    return '';
  };

  watch(
    () => props.clusterId,
    () => {
      if (props.clusterId) {
        fetchList({
          cluster_ids: [props.clusterId],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
