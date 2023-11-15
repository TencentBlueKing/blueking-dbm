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
    class="entry-config-dialog"
    height="450"
    :is-show="isShow"
    :quick-close="false"
    :title="t('修改入口配置')"
    width="640"
    @closed="handleClose">
    <BkLoading :loading="isLoading">
      <BkTable
        ref="tableRef"
        :border="['col', 'outer']"
        :cell-class="generateCellClass"
        class="entry-config-table-box"
        :columns="columns"
        :data="tableData" />
    </BkLoading>
    <template #footer>
      <BkButton
        class="mr-8"
        style="width: 64px;"
        theme="primary"
        @click="handleConfirm">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        style="width: 64px;"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx" generic="T extends Record<string, any>">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateClusterEntryConfig } from '@services/clusters';

  import { messageError, messageSuccess } from '@utils';

  import MultipleInput, { checkIp } from './MultipleInput.vue';
  import { useDetailData } from './useDetailData';

  export interface RowData {
    type: string,
    entry: string,
    ips: string,
    port: number,
  }

  interface Emits {
    (e: 'success'): void
  }

  interface Props {
    id?: number
    // eslint-disable-next-line vue/no-unused-properties
    getDetailInfo: (params: any) => Promise<T>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();
  const { isLoading, clusterId,  data: tableData, fetchResources } = useDetailData<T>();

  const tableRef = ref();

  const columns = [
    {
      label: t('访问入口'),
      field: 'entry',
      showOverflowTooltip: true,
    },
    {
      label: 'Bind IP',
      field: 'ips',
      render: ({ data }: {data: RowData}) => <MultipleInput v-model={data.ips} disabled={data.type !== 'dns'} />,
    },
  ];

  const { run: runUpdateClusterEntryConfig } = useRequest(updateClusterEntryConfig, {
    manual: true,
    onSuccess: (result) => {
      if (result?.cluster_id === undefined) {
        messageSuccess(t('修改成功'));
        emits('success');
        handleClose();
      }
    },
    onError: () => {
      messageError(t('修改失败'));
    },
  });

  watch(() => props.id, (id) => {
    clusterId.value = id;
  }, {
    immediate: true,
  });

  watch(isShow, (status) => {
    if (status) {
      setTimeout(() => {
        fetchResources();
      });
    }
  });


  const generateCellClass = (cell: { field: string}) => (cell.field === 'ips' ? 'entry-config-ips-column' : '');

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = () => {
    if (props.id !== undefined) {
      const dnsData = tableData.value.filter(item => item.type === 'dns');
      const dnsIps = dnsData.map(item => item.ips).map(item => item.split('\n'));
      if (dnsIps.every(item => item.every(row => checkIp(row)))) {
        const details = dnsData.reduce((results, item) => {
          const obj = {
            cluster_entry_type: item.type,
            domain_name: item.entry,
            target_instances: item.ips.split('\n').map(row => `${row}#${item.port}`),
          };
          results.push(obj);
          return results;
        }, [] as { cluster_entry_type: string, domain_name: string, target_instances: string[] }[]);
        const params = {
          cluster_id: props.id,
          cluster_entry_details: details,
        };
        runUpdateClusterEntryConfig(params);
      }
    }
  };
</script>

<style lang="less" scoped>
.entry-config-dialog {
  :deep(.bk-dialog-header) {
    padding: 18px 24px;
  }

  :deep(.bk-modal-close) {
    font-size: 24px;
  }
}

.entry-config-table-box {
  max-height:fit-content;
}
</style>
<style lang="less">
.entry-config-ips-column {
  .cell {
    padding: 0 !important;
    line-height: normal !important;
  }
}
</style>
