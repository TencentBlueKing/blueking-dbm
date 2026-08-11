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
  <BkDialog
    class="host-preview-dialog"
    :is-show="isShow"
    :title="title || t('主机预览')"
    :width="1100"
    @closed="handleClose">
    <div class="host-preview-content">
      <div class="host-preview-content-operations mb-16">
        <BkButton
          class="mr-8"
          @click="handleCopyAbnormalIps">
          {{ t('复制异常IP') }}
        </BkButton>
        <BkButton
          class="mr-8"
          @click="handleCopyIps">
          {{ t('复制所有IP') }}
        </BkButton>
        <BkInput
          v-model="state.keyword"
          clearable
          :placeholder="t('IP_主机名关键字')"
          type="search"
          @clear="handleChangePage(1)"
          @enter="handleChangePage(1)" />
      </div>
      <BkLoading :loading="state.isLoading">
        <PrimaryTable
          :bk-ui-settings="state.settings"
          :columns="columns"
          :data="state.data"
          :height="474"
          row-key="bk_host_id">
          <template #empty>
            <EmptyStatus
              :is-anomalies="state.isAnomalies"
              :is-searching="!!state.keyword"
              @clear-search="handleClearSearch"
              @refresh="fetchHostNodes" />
          </template>
        </PrimaryTable>
      </BkLoading>
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import type { HostNode } from '@services/types';

  import { useDefaultPagination } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { execCopy } from '@utils';

  interface Props {
    fetchNodes: (params: any) => Promise<HostNode[]>;
    fetchParams: Record<string, any>;
    title?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
  });
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  /**
   * 预览表格配置
   */
  const columns: PrimaryTableCol[] = [
    {
      colKey: 'bk_host_innerip',
      title: 'IP',
    },
    {
      cell: (_, { row }) => row.instance_num || '--',
      colKey: 'instance_num',
      title: t('每台主机节点数'),
    },
    {
      cell: (_, { row }) => row.bk_host_innerip_v6 || '--',
      colKey: 'bk_host_innerip_v6',
      title: 'IPv6',
    },
    {
      cell: (_, { row }) => row.bk_cloud_name || '--',
      colKey: 'bk_cloud_name',
      title: t('管控区域'),
    },
    {
      cell: (_, { row }) => {
        if (typeof row.status !== 'number') return '--';

        const text = [t('异常'), t('正常')];
        return <DbStatus theme={row.status === 1 ? 'success' : 'danger'}>{text[row.status as number]}</DbStatus>;
      },
      colKey: 'status',
      title: t('Agent状态'),
    },
    {
      cell: (_, { row }) => row.bk_host_name || '--',
      colKey: 'bk_host_name',
      title: t('主机名称'),
    },
    {
      cell: (_, { row }) => row.bk_os_name || '--',
      colKey: 'bk_os_name',
      title: t('OS名称'),
    },
    {
      cell: (_, { row }) => row.bk_cloud_vendor || '--',
      colKey: 'bk_cloud_vendor',
      title: t('所属云厂商'),
    },
    {
      cell: (_, { row }) => row.bk_os_type || '--',
      colKey: 'bk_os_type',
      title: t('OS类型'),
    },
    {
      cell: (_, { row }) => row.bk_host_id || '--',
      colKey: 'bk_host_id',
      title: t('主机ID'),
    },
    {
      cell: (_, { row }) => row.bk_agent_id || '--',
      colKey: 'bk_agent_id',
      title: 'Agent ID',
    },
  ];
  const state = reactive({
    data: [] as HostNode[],
    isAnomalies: false,
    isLoading: false,
    keyword: '',
    pagination: useDefaultPagination(),
    settings: {
      checked: ['bk_host_innerip', 'bk_host_innerip_v6', 'bk_host_name', 'status', 'instance_num'],
      fields: columns.map((item) => ({
        disabled: ['bk_host_innerip', 'bk_host_innerip_v6'].includes(item.colKey as string),
        field: item.colKey as string,
        label: item.title as string,
      })),
    },
  });

  watch(isShow, (isShowNew) => {
    if (isShowNew) {
      handleChangePage(1);
    }
  });

  const handleCopyAbnormalIps = () => {
    const abnormalIps = state.data.filter((item) => item.status === 0).map((item) => item.bk_host_innerip);
    if (abnormalIps.length > 0) {
      execCopy(abnormalIps.join('\n'), t('复制成功，共n条', { n: abnormalIps.length }));
    }
  };

  const handleCopyIps = () => {
    const ips = state.data.map((item) => item.bk_host_innerip);
    if (ips.length > 0) {
      execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
    }
  };

  /**
   * 获取节点列表
   */
  const fetchHostNodes = () => {
    state.isLoading = true;
    props
      .fetchNodes({
        ...props.fetchParams,
        ...state.pagination.getFetchParams(),
        keyword: state.keyword,
      })
      .then((res) => {
        state.data = res;
        state.isAnomalies = false;
      })
      .catch(() => {
        state.data = [];
        state.isAnomalies = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  /**
   * change page
   */
  const handleChangePage = (value: number) => {
    state.pagination.current = value;
    fetchHostNodes();
  };

  const handleClearSearch = () => {
    state.keyword = '';
    handleChangePage(1);
  };

  const handleClose = () => {
    isShow.value = false;
    state.keyword = '';
    state.pagination = useDefaultPagination();
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .host-preview-dialog {
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;
  }

  .host-preview-content {
    padding-bottom: 24px;

    .base-info-operations {
      .flex-center();
    }
  }
</style>
