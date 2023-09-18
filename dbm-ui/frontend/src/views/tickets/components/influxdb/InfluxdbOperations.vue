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

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Details {
    ticketDetails: {
      details: {
        instance_list: {
          bk_cloud_id: number,
          bk_host_id: number,
          instance_id: number,
          ip: string,
          port: number,
        }
      }
    }
  }


  const props = defineProps<Details>();
  const { t } = useI18n();

  const tableData = computed(() => props.ticketDetails?.details?.instance_list || []);
  const columns = [
    {
      label: t('实例ID'),
      field: 'instance_id',
    },
    {
      label: t('实例'),
      field: 'instance',
      render: ({ data }: { data: Details['ticketDetails']['details']['instance_list'] }) => {
        if (data.ip && data.port) {
          return `${data.ip}:${data.port}`;
        }
        return '--';
      },
    },
  ];
</script>
