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
  <SmartAction class="db-toolbox">
    <EditableTable
      ref="table"
      class="mb-20"
      :model="formData.tableData"
      :rules="rules">
      <EditableRow
        v-for="(item, index) in formData.tableData"
        :key="index">
        <WithRelatedClustersColumn
          v-model="item.cluster"
          role="proxy"
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <EditableColumn
          field="current_version"
          :label="t('当前版本')"
          :min-width="200"
          required>
          <EditableBlock
            v-model="item.current_version"
            :placeholder="t('自动生成')" />
        </EditableColumn>
        <TargetVersionColumn
          v-model="item.target_version"
          :row-data="item" />
        <OperationColumn
          v-model:table-data="formData.tableData"
          :create-row-method="createTableRow" />
      </EditableRow>
    </EditableTable>
    <BkFormItem
      v-bk-tooltips="t('存在业务连接时需要人工确认')"
      class="fit-content">
      <BkCheckbox
        v-model="formData.force"
        :false-label="false"
        true-label>
        <span class="safe-action-text">{{ t('检查业务连接') }}</span>
      </BkCheckbox>
    </BkFormItem>
    <TicketPayload v-model="formData.payload" />
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';

  import TargetVersionColumn from './components/TargetVersionColumn.vue';

  interface RowData {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    };
    current_version: string;
    target_version: {
      pkg_id: number;
      target_package: string;
    };
  }

  interface Props {
    ticketDetails?: Mysql.ProxyUpgrade;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      cluster_type: ClusterTypes.TENDBHA,
      id: 0,
      master_domain: '',
      related_clusters: [],
    },
    current_version: data.current_version || '',
    target_version: data.target_version || {
      pkg_id: 0,
      target_package: '',
    },
  });

  const defaultData = () => ({
    force: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const clusterMap = computed(() => {
    return formData.tableData.reduce<Record<string, string>>((acc, cur) => {
      Object.assign(acc, {
        [cur.cluster.master_domain]: cur.cluster.master_domain,
      });
      cur.cluster.related_clusters.forEach((item) => {
        Object.assign(acc, {
          [item.master_domain]: cur.cluster.master_domain, // 关联集群映射到所属集群
        });
      });
      return acc;
    }, {});
  });

  const rules = {
    'cluster.master_domain': [
      {
        message: '',
        trigger: 'blur',
        validator: (value: string) => {
          const target = clusterMap.value[value];
          if (target && target !== value) {
            return t('目标集群是集群target的关联集群_请勿重复添加', { target });
          }
          return true;
        },
      },
    ],
  };

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    force: boolean;
    infos: {
      cluster_ids: number[];
      display_info: {
        current_version: string;
        target_package: string;
      };
      pkg_id: number;
    }[];
  }>(TicketTypes.MYSQL_PROXY_UPGRADE);

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, force, infos } = props.ticketDetails;
        if (infos.length > 0) {
          formData.force = force;
          formData.tableData = infos.map((item) => {
            const clusterInfo = clusters[item.cluster_ids[0]];
            return createTableRow({
              cluster: {
                cluster_type: clusterInfo.cluster_type,
                id: clusterInfo.id,
                master_domain: clusterInfo.immute_domain,
                related_clusters: [],
              },
              current_version: item.display_info.current_version,
              target_version: {
                pkg_id: item.pkg_id,
                target_package: item.display_info.target_package,
              },
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!clusterMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              cluster_type: item.cluster_type,
              id: item.id,
              master_domain: item.master_domain,
              related_clusters: [],
            },
            current_version: item.proxies[0]?.version,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleSubmit = async () => {
    const result = await tableRef.value?.validate();
    if (result) {
      createTicketRun({
        details: {
          force: formData.force,
          infos: formData.tableData.map((item) => ({
            cluster_ids: [item.cluster.id, ...item.cluster.related_clusters.map((item) => item.id)],
            display_info: {
              current_version: item.current_version,
              target_package: item.target_version.target_package,
            },
            pkg_id: item.target_version.pkg_id,
          })),
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
