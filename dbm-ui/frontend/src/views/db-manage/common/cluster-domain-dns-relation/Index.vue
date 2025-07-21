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
  <span v-db-console="accessEntryDbConsole">
    <BkButton
      :disabled="data.isOffline"
      text
      @click="() => (isShow = true)">
      {{ t('手动配置域名 DNS 记录') }}
    </BkButton>
    <BkDialog
      class="cluster-domain-dns-relation"
      :is-show="isShow"
      quick-close
      show-mask
      :title="t('手动配置域名 DNS 记录')"
      :width="560"
      @closed="() => (isShow = false)">
      <BkLoading :loading="loading">
        <BkTable
          ref="tableRef"
          :cell-class="generateCellClass"
          class="entry-config-table-box"
          :data="tableData"
          :max-height="450"
          :show-overflow="false">
          <BkTableColumn
            field="entry"
            :label="t('访问入口')"
            :width="300">
            <template #default="{ data: rowData }: { data: ClusterEntryInfo }">
              {{ rowData.cluster_entry_type }}
              <template v-if="['master_entry', 'proxy_entry'].includes(rowData.role)">
                <BkTag
                  v-if="rowData.cluster_entry_type === 'polaris'"
                  class="entry-polary-tag"
                  size="small"
                  theme="success">
                  {{ t('北极星') }}
                </BkTag>
                <BkTag
                  v-else-if="['clb', 'clbDns'].includes(rowData.cluster_entry_type)"
                  class="entry-clb-tag"
                  size="small"
                  theme="success">
                  CLB
                </BkTag>
                <BkTag
                  v-else
                  size="small"
                  theme="info">
                  {{ t('主') }}
                </BkTag>
              </template>
              <BkTag
                v-if="rowData.role === 'slave_entry'"
                size="small"
                theme="success">
                {{ t('从') }}
              </BkTag>
              <BkTag
                v-if="rowData.role === 'node_entry'"
                size="small"
                theme="success">
                Nodes
              </BkTag>
              {{ rowData.entry }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="ips"
            label="Bind IP"
            :min-width="200"
            :show-overflow="false">
            <template #default="{ data: rowData }: { data: ClusterEntryInfo }">
              <RenderBindIps
                v-if="rowData.ips"
                :cluster-data="data"
                :data="rowData"
                @success="handleSuccess" />
              <span v-if="!rowData.ips">--</span>
            </template>
          </BkTableColumn>
        </BkTable>
      </BkLoading>
    </BkDialog>
  </span>
</template>
<script lang="tsx">
  const dbConsoleMap = {
    [ClusterTypes.DORIS]: 'doris.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.ES]: 'es.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.HDFS]: 'hdfs.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.KAFKA]: 'kafka.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.MONGO_REPLICA_SET]: 'mongodb.replicaSetList.modifyEntryConfiguration',
    [ClusterTypes.MONGO_SHARED_CLUSTER]: 'mongodb.sharedClusterList.modifyEntryConfiguration',
    // [ClusterTypes.ORACLE_PRIMARY_STANDBY]: 'oracle.singleClusterList.modifyEntryConfiguration',
    // [ClusterTypes.ORACLE_SINGLE_NONE]: 'oracle.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.PULSAR]: 'pulsar.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.REDIS]: 'redis.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.REDIS_INSTANCE]: 'redis.haClusterManage.modifyEntryConfiguration',
    [ClusterTypes.RIAK]: 'riak.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.SQLSERVER_HA]: 'sqlserver.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.SQLSERVER_SINGLE]: 'sqlserver.singleClusterList.modifyEntryConfiguration',
    [ClusterTypes.TENDBCLUSTER]: 'tendbCluster.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.TENDBHA]: 'mysql.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.TENDBSINGLE]: 'mysql.singleClusterList.modifyEntryConfiguration',
  };
</script>
<script setup lang="tsx">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterEntryDetailModel, { type DnsTargetDetails } from '@services/model/cluster-entry/cluster-entry-details';
  import { getClusterEntries } from '@services/source/clusterEntry';

  import { ClusterTypes } from '@common/const';

  import RenderBindIps from './components/RenderBindIps.vue';

  export interface ClusterEntryInfo {
    cluster_entry_type: string;
    entry: string;
    ips: string;
    port: number;
    role: string;
  }

  interface Props {
    data: {
      cluster_type: ClusterTypes;
      db_type: string;
      id: number;
      isOffline: boolean;
      permission: {
        access_entry_edit: boolean;
      };
    };
  }

  interface Slots {
    default: () => VNode;
  }

  type Emits = (e: 'success') => void;

  defineOptions({
    name: 'ClusterDomainDnsRelation',
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();
  defineSlots<Slots>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const generateCellClass = (cell: { field: string }) => (cell.field === 'ips' ? 'entry-config-ips-column' : '');

  const tableRef = ref();
  const tableData = ref<ClusterEntryInfo[]>([]);

  const accessEntryDbConsole = computed(() => {
    if (
      [
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ].includes(props.data.cluster_type)
    ) {
      return dbConsoleMap[ClusterTypes.REDIS];
    }
    return dbConsoleMap[props.data.cluster_type as keyof typeof dbConsoleMap] || false;
  });

  const { loading, run: fetchResources } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (data) => {
      tableData.value = data
        .filter((item) => item.cluster_entry_type === 'dns')
        .map((item) => ({
          cluster_entry_type: item.cluster_entry_type,
          entry: item.entry,
          ips: (item as ClusterEntryDetailModel<DnsTargetDetails>).target_details.map((row) => row.ip).join('\n'),
          port: (item as ClusterEntryDetailModel<DnsTargetDetails>).target_details[0]?.port,
          role: item.role,
        }))
        .sort((a) => (a.role === 'master_entry' ? -1 : 1));
    },
  });

  watch(isShow, () => {
    if (isShow.value && props.data.id !== 0) {
      fetchResources({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_id: props.data.id,
      });
    }
  });

  const handleSuccess = () => {
    emits('success');
  };
</script>
<style lang="less">
  .cluster-domain-dns-relation {
    .bk-modal-footer {
      display: none;
    }

    .entry-clb-tag {
      color: #8e3aff;
      cursor: pointer;
      background-color: #f2edff;

      &:hover {
        color: #8e3aff;
        background-color: #e3d9fe;
      }
    }

    .entry-polary-tag {
      color: #3a84ff;
      cursor: pointer;
      background-color: #edf4ff;

      &:hover {
        color: #3a84ff;
        background-color: #e1ecff;
      }
    }
  }
</style>
