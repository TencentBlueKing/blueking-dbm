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
    <BkLoading :loading="loading">
      <BkTable
        ref="tableRef"
        :border="['col', 'outer']"
        :cell-class="generateCellClass"
        class="entry-config-table-box"
        :data="tableData">
        <BkTableColumn
          field="entry"
          :label="t('访问入口')"
          :width="263">
          <template #default="{ data }: { data: ClusterEntryInfo }">
            <span>
              <slot
                v-if="slots.prepend"
                :data="data"
                name="prepend" />
              {{ data.entry }}
            </span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="ips"
          label="Bind IP"
          :width="263">
          <template #default="{ data }: { data: ClusterEntryInfo }">
            <RenderBindIps
              v-if="data.ips"
              :data="data"
              v-bind="props"
              @success="handleSuccess" />
          </template>
        </BkTableColumn>
      </BkTable>
    </BkLoading>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterEntryDetailModel, { type DnsTargetDetails } from '@services/model/cluster-entry/cluster-entry-details';
  import { getClusterEntries } from '@services/source/clusterEntry';

  import type { DBTypes } from '@common/const';

  import RenderBindIps from './RenderBindIps.vue';

  export interface ClusterEntryInfo {
    type: string;
    entry: string;
    role: string;
    ips: string;
    port: number;
  }

  interface Props {
    id: number;
    bizId: number;
    resource: DBTypes;
    permission: boolean;
    sort?: (data: ClusterEntryInfo[]) => ClusterEntryInfo[];
  }

  interface Emits {
    (e: 'success'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    sort: (data: ClusterEntryInfo[]) => data,
  });

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    prepend?: (data: ClusterEntryInfo) => VNode | VNode[];
  }>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const tableRef = ref();
  const tableData = ref<ClusterEntryInfo[]>([]);

  const { run: fetchResources, loading } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (data) => {
      tableData.value = props.sort(
        data.map((item) => ({
          type: item.cluster_entry_type,
          entry: item.entry,
          role: item.role,
          ips: item.isDns
            ? (item as ClusterEntryDetailModel<DnsTargetDetails>).target_details.map((row) => row.ip).join('\n')
            : '',
          port: (item as ClusterEntryDetailModel<DnsTargetDetails>).target_details[0]?.port,
        })),
      );
    },
  });

  watch(isShow, () => {
    if (isShow.value && props.id !== 0) {
      fetchResources({
        cluster_id: props.id,
        bk_biz_id: props.bizId,
      });
    }
  });

  const generateCellClass = (cell: { field: string }) => (cell.field === 'ips' ? 'entry-config-ips-column' : '');

  const handleSuccess = () => {
    emits('success');
  };
</script>

<style lang="less" scoped>
  .entry-config-table-box {
    max-height: fit-content;
  }
</style>
<style lang="less">
  .entry-config-dialog {
    .bk-modal-footer {
      display: none;
    }
  }
</style>
