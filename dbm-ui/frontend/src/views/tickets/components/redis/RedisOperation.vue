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
    :columns="rederColumns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { computed, type PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { RedisKeysDetails, TicketDetails } from '@services/types/ticket';

  import { TicketTypes } from '@common/const';
  const props = defineProps({
    ticketDetails: {
      required: true,
      type: Object as PropType<TicketDetails<RedisKeysDetails>>,
    },
  });

  const { t } = useI18n();

  /**
   * redis-rules | clusters 合并参数
   */
  type RedisAssign = {
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

  /**
   * 提取key、删除key需求信息
   */
  const columns = [{
    label: t('集群名称'),
    field: 'domain',
    showOverflowTooltip: false,
    render: ({ data } : { data: RedisAssign }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
  }, {
    label: t('包含Key'),
    field: 'white_regex',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('排除Key'),
    field: 'black_regex',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }];

  /**
   * 从结果文件删除的需求信息
   */
  const fileColumns = [{
    label: t('文件'),
    field: 'path',
  }, {
    label: t('大小'),
    field: 'total_size',
    sort: true,
  }, {
    label: t('集群名称'),
    field: 'domain',
    showOverflowTooltip: false,
    render: ({ data } : { data: RedisAssign }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
  }, {
    label: t('提取时间'),
    field: 'create_at',
    sort: true,
  }];

  /**
   * 备份的需求信息
   */
  const backupColumns = [{
    label: t('域名'),
    field: 'domain',
    showOverflowTooltip: false,
    render: ({ data } : { data: RedisAssign }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
  }, {
    label: t('架构版本'),
    field: 'cluster_type_name',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('备份目标'),
    field: 'target',
  }, {
    label: t('备份类型'),
    field: 'backup_type',
    render: ({ cell }: { cell: 'normal_backup' | 'forever_backup' }) => {
      const backupType = {
        normal_backup: t('常规备份'),
        forever_backup: t('长期备份'),
      };
      return (
        <span>{backupType[cell]}</span>
      );
    },
  }];

  // 清档
  const purgeColumns = [{
    label: t('域名'),
    field: 'domain',
    showOverflowTooltip: false,
    render: ({ data } : { data: RedisAssign }) => (
      <div class="cluster-name text-overflow"
        v-overflow-tips={{
          content: `
            <p>${t('域名')}：${data.domain}</p>
            ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
          `,
          allowHTML: true,
      }}>
        <span>{data.domain}</span><br />
        <span class="cluster-name__alias">{data.name}</span>
      </div>
    ),
  }, {
    label: t('架构版本'),
    field: 'cluster_type_name',
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }, {
    label: t('强制清档'),
    field: 'force',
    render: ({ cell }: { cell: string }) => <span>{cell ? t('是') : t('否')}</span>,
  }, {
    label: t('清档前备份'),
    field: 'backup',
    render: ({ cell }: { cell: string }) => <span>{cell ? t('是') : t('否')}</span>,
  }];

  const rederColumns = computed(() => {
    if (props.ticketDetails?.ticket_type === TicketTypes.REDIS_BACKUP) {
      return backupColumns;
    }
    if (props.ticketDetails?.details?.delete_type === 'files') {
      return fileColumns;
    }
    if (props.ticketDetails?.ticket_type === TicketTypes.REDIS_PURGE) {
      return purgeColumns;
    }
    return columns;
  });

  const dataList = computed(() => {
    const rules = props.ticketDetails?.details?.rules || [];
    const clusters = props.ticketDetails?.details?.clusters || {};
    const createAt = props.ticketDetails?.create_at;
    return rules.map(item => Object.assign({ create_at: createAt }, item, clusters[item.cluster_id]));
  });
</script>

<style lang="less" scoped>
  @import "../ticketDetails.less";

  :deep(.cluster-name) {
    padding: 8px 0;
    line-height: 16px;

    &__alias {
      color: @light-gray;
    }
  }
</style>
