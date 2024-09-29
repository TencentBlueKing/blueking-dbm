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
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { utcDisplayTime } from '@utils';

  interface Props{
    ticketDetails: TicketModel<Redis.Purge>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_PURGE,
    inheritAttrs: false
  })

  const { t } = useI18n();

  /**
   * redis-rules | clusters 合并参数
   */
  interface RedisAssign {
    alias: string,
    bk_biz_id: number,
    black_regex: string,
    cluster_id: number,
    cluster_type: string,
    cluster_type_name: string,
    creator: string,
    db_module_id: number,
    domain: string,
    id: number,
    immute_domain: string,
    major_version: string,
    name: string,
    path: string,
    total_size: string,
    updater: string,
    white_regex: string,
    create_at: string,
  }

  // 清档
  const columns = [
    {
      label: t('域名'),
      field: 'domain',
      showOverflowTooltip: false,
      render: ({ data } : { data: RedisAssign }) => data.domain,
    },
    {
      label: t('架构版本'),
      field: 'cluster_type_name',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('强制清档'),
      field: 'force',
      render: ({ cell }: { cell: string }) => <span>{cell ? t('是') : t('否')}</span>,
    },
    {
      label: t('清档前备份'),
      field: 'backup',
      render: ({ cell }: { cell: string }) => <span>{cell ? t('是') : t('否')}</span>,
    },
  ];


  const dataList = computed(() => {
    const rules = props.ticketDetails?.details?.rules || [];
    const clusters = props.ticketDetails?.details?.clusters || {};
    const createAt = props.ticketDetails?.create_at;
    return rules.map(item => Object.assign({ create_at: utcDisplayTime(createAt) }, item, clusters[item.cluster_id]));
  });
</script>
