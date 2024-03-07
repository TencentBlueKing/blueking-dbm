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
    <TableInput :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBatchSqlserverDbs } from '@services/source/sqlserver';

  import TableInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    clusterIdList: number[];
    dbPatterns: string[];
    ignoreBackupDbs: string[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('备份源不能为空'),
    },
  ];

  const localValue = ref<ServiceReturnType<typeof getBatchSqlserverDbs>>({});

  const { loading: isLoading, run: fetchBatchSqlserverDbs } = useRequest(getBatchSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      localValue.value = data;
    },
  });

  watch(
    () => [props.clusterIdList, props.dbPatterns, props.ignoreBackupDbs],
    () => {
      if (props.clusterIdList.length > 0 && props.dbPatterns.length > 0 && props.ignoreBackupDbs.length > 0) {
        fetchBatchSqlserverDbs({
          cluster_ids: props.clusterIdList,
          db_list: props.dbPatterns,
          ignore_db_list: props.ignoreBackupDbs,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
