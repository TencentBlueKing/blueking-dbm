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
    :title="$t('主机预览')"
    @closed="handleClose">
    <div class="host-preview-content">
      <div class="host-preview-content-operations mb-16">
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
      </div>
      <BkLoading :loading="loading">
        <DbOriginalTable
          :columns="columns"
          :data="data"
          :height="474"
          :is-anomalies="isAnomalies"
          :settings="settings"
          @refresh="fetchHosts" />
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
  import { useRequest } from 'vue-request';

  import { getHostDetails } from '@services/ip';

  import { useCopy } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';

  import type { TableColumnRender } from '@/types/bkui-vue';

  interface Props {
    hostIds: number[],
    bizId: number,
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>('isShow');

  const { t } = useI18n();
  const copy = useCopy();

  const isAnomalies = ref(false);

  /**
   * 预览表格配置
   */
  const columns = [{
    label: 'IP',
    field: 'ip',
  }, {
    label: 'IPv6',
    field: 'ipv6',
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('管控区域'),
    field: 'bk_cloud_name',
    render: ({ cell }: any) => <span>{cell?.name || '--'}</span>,
  }, {
    label: t('Agent状态'),
    field: 'alive',
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
  const settings = {
    fields: columns.map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['ip'].includes(item.field),
    })),
    checked: ['ip', 'bk_host_name', 'alive'],
  };

  const {
    data,
    loading,
    run: fetchData,
  } = useRequest(getHostDetails, {
    manual: true,
    onError: () => {
      isAnomalies.value = true;
    },
    onSuccess: () => {
      isAnomalies.value = false;
    },
  });

  watch(isShow, () => {
    isShow.value && fetchHosts();
  });

  const fetchHosts = () => {
    fetchData({
      mode: 'all',
      host_list: props.hostIds.map(hostId => ({
        host_id: hostId,
        meta: {
          bk_biz_id: props.bizId,
          scope_id: props.bizId,
          scope_type: 'biz',
        },
      })),
      scope_list: [{
        scope_id: props.bizId,
        scope_type: 'biz',
      }],
    });
  };

  function handleCopyAbnormalIps() {
    const abnormalIps = (data.value || []).filter(item => item.alive === 0).map(item => item.ip);
    if (abnormalIps.length === 0) return;
    copy(abnormalIps.join('\n'));
  }

  function handleCopyIps() {
    const ips = (data.value || []).map(item => item.ip);
    if (ips.length === 0) return;
    copy(ips.join('\n'));
  }

  function handleClose() {
    isShow.value = false;
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

    .host-preview-content-operations {
      .flex-center();
    }
  }
</style>
