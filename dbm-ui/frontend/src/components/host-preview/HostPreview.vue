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
          {{ $t('复制全部IP') }}
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
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostNode } from '@services/types/common';

  import { useCopy, useDefaultPagination } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';

  import type { TableColumnRender } from '@/types/bkui-vue';

  const props = defineProps({
    fetchParams: {
      type: Object,
      required: true,
    },
    fetchNodes: {
      type: Function as PropType<(params: any) => Promise<HostNode[]>>,
      required: true,
    },
    isShow: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
  });

  const emits = defineEmits(['update:isShow']);

  const { t } = useI18n();
  const copy = useCopy();

  /**
   * 预览表格配置
   */
  const columns = [{
    label: 'IP',
    field: 'bk_host_innerip',
  }, {
    label: t('每台主机节点数'),
    field: 'instance_num',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: 'IPv6',
    field: 'bk_host_innerip_v6',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('云区域'),
    field: 'bk_cloud_name',
    render: ({ cell }: any) => <span>{cell?.name || '--'}</span>,
  }, {
    label: t('Agent状态'),
    field: 'status',
    render: ({ cell }: { cell: number }) => {
      if (typeof cell !== 'number') return '--';

      const text = [t('异常'), t('正常')];
      return <DbStatus theme={cell === 1 ? 'success' : 'danger'}>{text[cell]}</DbStatus>;
    },
  }, {
    label: t('主机名称'),
    field: 'bk_host_name',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('OS名称'),
    field: 'bk_os_name',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('所属云厂商'),
    field: 'bk_cloud_vendor',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('OS类型'),
    field: 'bk_os_type',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('主机ID'),
    field: 'bk_host_id',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: 'Agent ID',
    field: 'bk_agent_id',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }];
  const state = reactive({
    isLoading: false,
    keyword: '',
    settings: {
      fields: columns.map(item => ({
        label: item.label,
        field: item.field,
        disabled: ['bk_host_innerip', 'bk_host_innerip_v6'].includes(item.field),
      })),
      checked: ['bk_host_innerip', 'bk_host_innerip_v6', 'bk_host_name', 'status', 'instance_num'],
    },
    data: [] as HostNode[],
    pagination: useDefaultPagination(),
    isAnomalies: false,
  });

  watch(() => props.isShow, () => {
    props.isShow && handleChangePage(1);
  });

  function handleCopyAbnormalIps() {
    const abnormalIps = state.data.filter(item => item.status === 0).map(item => item.bk_host_innerip);
    if (abnormalIps.length === 0) return;
    copy(abnormalIps.join('\n'));
  }

  function handleCopyIps() {
    const ips = state.data.map(item => item.bk_host_innerip);
    if (ips.length === 0) return;
    copy(ips.join('\n'));
  }

  /**
   * 获取节点列表
   */
  function fetchHostNodes() {
    state.isLoading = true;
    props.fetchNodes({
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
    emits('update:isShow', false);
    state.keyword = '';
    state.pagination = useDefaultPagination();
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

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
