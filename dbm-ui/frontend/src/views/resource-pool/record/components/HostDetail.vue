<template>
  <BkButton
    text
    theme="primary"
    @click="handleShowDetail">
    {{ data.bk_host_ids.length }}
  </BkButton>
  <BkDialog
    :is-show="isShowDetail"
    :title="t('主机预览')"
    :width="dialogWidth">
    <BkLoading :loading="isHostListLoading">
      <div class="mb-12">
        <BkButton @click="handleCopyAbnormalIp">
          {{ t('复制异常 IP') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleCopyAllIp">
          {{ t('复制全部 IP') }}
        </BkButton>
      </div>
      <BkTable
        class="mb-24"
        :columns="tableColumn"
        :data="hostList" />
    </BkLoading>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx">
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchHostListByHostId } from '@services/dbResource';
  import type OperationModel from '@services/model/db-resource/Operation';
  import type { HostDetails } from '@services/types/ip';

  import DbStatus from '@components/db-status/index.vue';

  import {
    execCopy,
    messageWarn,
  } from '@utils';

  interface Props {
    data: OperationModel
  }

  const props = defineProps<Props>();
  const { t } = useI18n();

  const isShowDetail = ref(false);
  const dialogWidth = Math.ceil(window.innerWidth * 0.8);

  const tableColumn = [
    {
      label: 'IP',
      field: 'ip',
      fixed: 'left',
      width: 150,
    },
    {
      label: 'IPV6',
      field: 'ipv6',
      render: ({ data }: { data: HostDetails}) => data.ipv6 || '--',
    },
    {
      label: '管控区域',
      field: 'cloud_area.name',
    },
    {
      label: 'Agent 状态',
      field: 'agent',
      render: ({ data }: { data: HostDetails}) => {
        const info = data.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: '主机名称',
      field: 'host_name',
    },
    {
      label: 'OS 名称',
      field: 'os_name',
    },
  ];

  const {
    loading: isHostListLoading,
    data: hostList,
    run: fetchHostList,
  } = useRequest(fetchHostListByHostId, {
    manual: true,
  });

  const fetchData = () => {
    if (props.data.bk_host_ids.length < 1) {
      return;
    }
    fetchHostList({
      bk_host_ids: props.data.bk_host_ids.join(','),
    });
  };

  const handleShowDetail = () => {
    isShowDetail.value = true;
    fetchData();
  };

  const handleCopyAbnormalIp = () => {
    const ipList = hostList.value?.reduce((result, item) => {
      if (item.alive !== 1) {
        result.push(item.ip);
      }
      return result;
    }, [] as string[]);
    if (!ipList || ipList.length < 1) {
      messageWarn(t('暂无可复制异常 IP'));
      return;
    }
    execCopy(ipList?.join('\n'));
  };

  const handleCopyAllIp = () => {
    const ipList = hostList.value?.map(hostItem => hostItem.ip);
    if (!ipList || ipList.length < 1) {
      messageWarn(t('暂无可复制 IP'));
      return;
    }
    execCopy(ipList?.join('\n'));
  };

  const handleClose = () => {
    isShowDetail.value = false;
  };
</script>

