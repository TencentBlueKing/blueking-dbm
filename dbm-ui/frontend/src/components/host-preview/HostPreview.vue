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
    :title="title || $t('主机预览')"
    :width="1100"
    @closed="handleClose">
    <div class="host-preview-content">
      <div class="host-preview-content__operations mb-16">
        <BkButton
          class="mr-8"
          @click="handleCopyAbnormalIps">
          {{ $t('复制异常IP') }}
        </BkButton>
        <BkButton
          class="mr-8"
          @click="handleCopyIps">
          {{ $t('复制所有IP') }}
        </BkButton>
        <BkInput
          v-model="state.keyword"
          clearable
          :placeholder="$t('IP_主机名关键字')"
          type="search"
          @clear="handleChangePage(1)"
          @enter="handleChangePage(1)" />
      </div>
      <BkLoading :loading="state.isLoading">
        <DbOriginalTable
          :columns="columns"
          :data="state.data"
          :height="474"
          :is-anomalies="state.isAnomalies"
          :is-searching="!!state.keyword"
          :settings="state.settings"
          @clear-search="handleClearSearch"
          @page-limit-change="handeChangeLimit"
          @page-value-change="handleChangePage"
          @refresh="fetchHostNodes" />
      </BkLoading>
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ $t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { HostNode } from '@services/types';

  import { useDefaultPagination } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';

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
  const columns = [
    {
      field: 'bk_host_innerip',
      label: 'IP',
    },
    {
      field: 'instance_num',
      label: t('每台主机节点数'),
      render: ({ data }: { data: HostNode }) => data.instance_num || '--',
    },
    {
      field: 'bk_host_innerip_v6',
      label: 'IPv6',
      render: ({ data }: { data: HostNode }) => data.bk_host_innerip_v6 || '--',
    },
    {
      field: 'bk_cloud_name',
      label: t('管控区域'),
      render: ({ data }: { data: HostNode }) => data.bk_cloud_name || '--',
    },
    {
      field: 'status',
      label: t('Agent状态'),
      render: ({ data }: { data: HostNode }) => {
        if (typeof data.status !== 'number') return '--';

        const text = [t('异常'), t('正常')];
        return <DbStatus theme={data.status === 1 ? 'success' : 'danger'}>{text[data.status]}</DbStatus>;
      },
    },
    {
      field: 'bk_host_name',
      label: t('主机名称'),
      render: ({ data }: { data: HostNode }) => data.bk_host_name || '--',
    },
    {
      field: 'bk_os_name',
      label: t('OS名称'),
      render: ({ data }: { data: HostNode }) => data.bk_os_name || '--',
    },
    {
      field: 'bk_cloud_vendor',
      label: t('所属云厂商'),
      render: ({ data }: { data: HostNode }) => data.bk_cloud_vendor || '--',
    },
    {
      field: 'bk_os_type',
      label: t('OS类型'),
      render: ({ data }: { data: HostNode }) => data.bk_os_type || '--',
    },
    {
      field: 'bk_host_id',
      label: t('主机ID'),
      render: ({ data }: { data: HostNode }) => data.bk_host_id || '--',
    },
    {
      field: 'bk_agent_id',
      label: 'Agent ID',
      render: ({ data }: { data: HostNode }) => data.bk_agent_id || '--',
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
        disabled: ['bk_host_innerip', 'bk_host_innerip_v6'].includes(item.field),
        field: item.field,
        label: item.label,
      })),
    },
  });

  watch(isShow, (isShowNew) => {
    if (isShowNew) {
      handleChangePage(1);
    }
  });

  function handleCopyAbnormalIps() {
    const abnormalIps = state.data.filter((item) => item.status === 0).map((item) => item.bk_host_innerip);
    if (abnormalIps.length > 0) {
      execCopy(abnormalIps.join('\n'), t('复制成功，共n条', { n: abnormalIps.length }));
    }
  }

  function handleCopyIps() {
    const ips = state.data.map((item) => item.bk_host_innerip);
    if (ips.length > 0) {
      execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
    }
  }

  /**
   * 获取节点列表
   */
  function fetchHostNodes() {
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
  }

  /**
   * change page
   */
  function handleChangePage(value: number) {
    state.pagination.current = value;
    fetchHostNodes();
  }

  /**
   * change limit
   */
  function handeChangeLimit(value: number) {
    state.pagination.limit = value;
    handleChangePage(1);
  }

  function handleClearSearch() {
    state.keyword = '';
    handleChangePage(1);
  }

  function handleClose() {
    isShow.value = false;
    state.keyword = '';
    state.pagination = useDefaultPagination();
  }
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

    &__operations {
      .flex-center();
    }
  }
</style>
