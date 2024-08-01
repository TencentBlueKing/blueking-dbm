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
  <DbOriginalTable
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';

  interface Props {
    configRules?: OpenareaTemplateModel['config_rules'];
  }

  type RowData = OpenareaTemplateModel['config_rules'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => _.sortBy(props.configRules || [], 'source_db'));

  const columns = [
    {
      label: t('克隆 DB'),
      minWidth: 150,
      width: 200,
      field: 'source_db',
    },
    {
      label: t('克隆表数据'),
      field: 'data_tblist',
      render: ({ data }: { data: RowData }) => (
        <span>
          { data.data_tblist.length > 0 ? data.data_tblist.join(',') : '--' }
        </span>
      ),
    },
    {
      label: t('生成的目标 DB 范式'),
      field: 'target_db_pattern',
    },
  ];
</script>
