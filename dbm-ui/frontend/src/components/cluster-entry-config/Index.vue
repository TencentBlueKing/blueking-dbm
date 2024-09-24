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
  <DbIcon
    v-bk-tooltips="t('查看域名/IP对应关系')"
    type="visible1"
    @click="() => (isShow = true)" />
  <BkDialog
    class="entry-config-dialog"
    draggable
    :is-show="isShow"
    :quick-close="false"
    :show-mask="false"
    :title="t('查看域名/IP对应关系')"
    :width="640"
    @closed="() => (isShow = false)">
    <BkLoading :loading="isLoading">
      <BkTable
        ref="tableRef"
        :border="['col', 'outer']"
        :cell-class="generateCellClass"
        class="entry-config-table-box"
        :columns="columns"
        :data="tableData" />
    </BkLoading>
  </BkDialog>
</template>

<script setup lang="tsx">
  import type { JSX } from 'vue/jsx-runtime';
  import { useI18n } from 'vue-i18n';

  import type { DBTypes } from '@common/const';

  import RenderBindIps from './RenderBindIps.vue';

  export interface RowData {
    type: string,
    entry: string,
    role: string,
    ips: string,
    port: number,
  }

  interface Emits {
    (e: 'success'): void
  }

  interface Props {
    id?: number
    resource: DBTypes;
    permission: boolean;
    renderEntry?: (data: RowData) => JSX.Element | string;
    getDetailInfo: (params: any) => Promise<{
      cluster_entry_details: {
        cluster_entry_type: string,
        entry: string,
        role: string,
        target_details: {
          ip: string,
          port: number
        }[]
      }[]
    }>;
    sort?: (data: RowData[]) => RowData[];
  }

  const props = withDefaults(defineProps<Props>(), {
    id: 0,
    renderEntry: (data: RowData) => data.entry,
    sort: (data: RowData[]) => data,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const tableRef = ref();
  const isLoading = ref(false);
  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('访问入口'),
      field: 'entry',
      width: 263,
      showOverflowTooltip: true,
      render: ({ data }: { data: RowData }) => props.renderEntry(data),
    },
    {
      label: 'Bind IP',
      field: 'ips',
      width: 263,
      render: ({ data }: {data: RowData}) => (
        <RenderBindIps
          v-model={props.id}
          data={data}
          permission={props.permission}
          resource={props.resource}
          onSuccess={handleSuccess} />
      )
    },
  ];

  watch(isShow, () => {
    if (isShow.value && props.id !== 0) {
      fetchResources();
    }
  });

  const fetchResources = () => {
    isLoading.value = true;
    props.getDetailInfo({
      id: props.id,
    })
      .then((res) => {
        const data = res.cluster_entry_details.map(item => ({
          type: item.cluster_entry_type,
          entry: item.entry,
          role: item.role,
          ips: item.target_details.map(row => row.ip).join('\n'),
          port: item.target_details[0].port,
        }));
        tableData.value = props.sort(data);
      })
      .catch(() => {
        tableData.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const generateCellClass = (cell: { field: string}) => (cell.field === 'ips' ? 'entry-config-ips-column' : '');

  const handleSuccess = () => {
    emits('success');
  }
</script>

<style lang="less" scoped>
  .entry-config-table-box {
    max-height: fit-content;
  }
</style>
<style lang="less">
  .entry-config-ips-column {
    .cell {
      padding: 0 !important;
      line-height: normal !important;
    }
  }

  .entry-config-dialog {
    .bk-modal-footer {
      display: none;
    }
  }
</style>
