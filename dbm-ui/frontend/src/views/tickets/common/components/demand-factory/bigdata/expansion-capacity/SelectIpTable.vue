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
  <BkTable
    :columns="tableColumns"
    :data="data" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      ip: string,
      alive: number,
      bk_disk: number,
      instance_num?: number,
    }[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowInstanceColumn = props.data.find(item => item.instance_num !== undefined);

  const tableColumns = [
    {
      label: t('节点 IP'),
      field: 'ip',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: {data: { alive: number }}) => <span>{data.alive === 1 ? t('正常') : t('异常')}</span>,
    },
    {
      label: t('磁盘_GB'),
      field: 'bk_disk',
    },
  ];
  if (isShowInstanceColumn) {
    tableColumns.splice(1, 0, {
      label: t('每台主机实例数'),
      field: 'instance_num',
    });
  }

</script>
