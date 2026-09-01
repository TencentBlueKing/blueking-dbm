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
    :title="t('主机预览')"
    width="80%"
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
      </div>
      <BkLoading :loading="loading">
        <PrimaryTable
          :bk-ui-settings="settings"
          :columns="columns"
          :data="data"
          :height="474">
          <template #empty>
            <EmptyStatus
              :is-anomalies="isAnomalies"
              :is-searching="false"
              @refresh="fetchHosts" />
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
  import { useRequest } from 'vue-request';

  import { getHostDetails } from '@services/source/ipchooser';
  import type { HostInfo } from '@services/types';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { execCopy } from '@utils';

  interface Props {
    hostIds: number[];
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>('isShow');

  const { t } = useI18n();

  const isAnomalies = ref(false);

  const columns: PrimaryTableCol[] = [
    {
      colKey: 'ip',
      title: 'IP',
    },
    {
      cell: (_, { row }) => (row as HostInfo).ipv6 || '--',
      colKey: 'ipv6',
      title: 'IPv6',
    },
    {
      cell: (_, { row }) => (row as HostInfo).cloud_area.name || '--',
      colKey: 'bk_cloud_name',
      title: t('管控区域'),
    },
    {
      cell: (_, { row }) => {
        const data = row as HostInfo;
        if (typeof data.alive !== 'number') return '--';

        const text = [t('异常'), t('正常')];
        return <DbStatus theme={data.alive === 1 ? 'success' : 'danger'}>{text[data.alive]}</DbStatus>;
      },
      colKey: 'alive',
      title: t('Agent状态'),
    },
    {
      cell: (_, { row }) => (row as HostInfo).host_name || '--',
      colKey: 'host_name',
      title: t('主机名称'),
    },
    {
      cell: (_, { row }) => (row as HostInfo).os_name || '--',
      colKey: 'os_name',
      title: t('OS名称'),
    },
    {
      cell: (_, { row }) => (row as HostInfo).cloud_vendor || '--',
      colKey: 'cloud_vendor',
      title: t('所属云厂商'),
    },
    {
      cell: (_, { row }) => (row as HostInfo).os_type || '--',
      colKey: 'os_type',
      title: t('OS类型'),
    },
    {
      cell: (_, { row }) => String((row as HostInfo).host_id ?? '--'),
      colKey: 'host_id',
      title: t('主机ID'),
    },
    {
      cell: (_, { row }) => String((row as HostInfo).agent_id ?? '--'),
      colKey: 'agent_id',
      title: 'Agent ID',
    },
  ];
  const settings = {
    checked: ['ip', 'bk_host_name', 'alive'],
    fields: columns.map((item) => ({
      disabled: ['ip'].includes(item.colKey as string),
      field: item.colKey as string,
      label: item.title as string,
    })),
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
    if (isShow.value) {
      fetchHosts();
    }
  });

  const fetchHosts = () => {
    fetchData({
      host_list: props.hostIds.map((hostId) => ({
        host_id: hostId,
      })),
      mode: 'all',
      scope_list: [],
    });
  };

  const handleCopyAbnormalIps = () => {
    const abnormalIps = (data.value || []).filter((item) => item.alive === 0).map((item) => item.ip);
    if (abnormalIps.length === 0) {
      return;
    }
    execCopy(abnormalIps.join('\n'), t('复制成功，共n条', { n: abnormalIps.length }));
  };

  const handleCopyIps = () => {
    const ips = (data.value || []).map((item) => item.ip);
    if (ips.length === 0) {
      return;
    }
    execCopy(ips.join('\n'), t('复制成功，共n条', { n: ips.length }));
  };

  const handleClose = () => {
    isShow.value = false;
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

    .host-preview-content-operations {
      .flex-center();
    }
  }
</style>
