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
    :is-show="isShow"
    :quick-close="false"
    :show-mask="false"
    :title="t('查看域名/IP对应关系')"
    :width="640"
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
  </BkDialog>
</template>

<script
  setup
  lang="tsx"
  generic="
    T extends
      | ResourceItem
      | ResourceRedisItem
      | SpiderModel
      | EsModel
      | HdfsModel
      | KafkaModel
      | PulsarModel
      | SqlServerHaClusterDetailModel
      | SqlServerSingleClusterDetailModel
  ">
  import { useI18n } from 'vue-i18n';

  import EsModel from '@services/model/es/es';
  import HdfsModel from '@services/model/hdfs/hdfs';
  import KafkaModel from '@services/model/kafka/kafka';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import SpiderModel from '@services/model/spider/spider';
  import SqlServerHaClusterDetailModel from '@services/model/sqlserver/sqlserver-ha-cluster-detail';
  import SqlServerSingleClusterDetailModel from '@services/model/sqlserver/sqlserver-single-cluster-detail';
  import type { ResourceItem, ResourceRedisItem } from '@services/types';

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
    dbConsole: string;
    resource: DBTypes;
    permission: boolean;
    getDetailInfo: (params: any) => Promise<T>
  }

  const props = withDefaults(defineProps<Props>(), {
    id: 0,
    disabled: true,
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
      render: ({ data }: {data: RowData}) => {
        if (data.role === 'master_entry') {
          return (
            <>
              <bk-tag size="small" theme="success">{ t('主') }</bk-tag>{ data.entry }
            </>
          )
        }
        return (
          <>
            <bk-tag size="small" theme="info">{ t('从') }</bk-tag>{ data.entry }
          </>
        )
      },
    },
    {
      label: 'Bind IP',
      field: 'ips',
      width: 263,
      render: ({ data }: {data: RowData}) => (
        <RenderBindIps
          v-model={props.id}
          data={data}
          dbConsole={props.dbConsole}
          permission={props.permission}
          resource={props.resource}
          onSuccess={handleSuccess} />
      )
    },
  ];

  watch(() => props.id, (id) => {
    if (id) {
      fetchResources();
    }
  }, {
    immediate: true,
  });

  const fetchResources = () => {
    isLoading.value = true;
    props.getDetailInfo({
      id: props.id,
    })
      .then((res: T) => {
        tableData.value = res.cluster_entry_details.map(item => ({
          type: item.cluster_entry_type,
          entry: item.entry,
          role: item.role,
          ips: item.target_details.map(row => row.ip).join('\n'),
          port: item.target_details[0].port,
        }));
      })
      .catch(() => {
        tableData.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const generateCellClass = (cell: { field: string}) => (cell.field === 'ips' ? 'entry-config-ips-column' : '');

  const handleClose = () => {
    isShow.value = false;
  };

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
