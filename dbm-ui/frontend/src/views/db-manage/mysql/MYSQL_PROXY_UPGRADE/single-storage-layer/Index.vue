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
      :model="formData.tableData">
      <EditableRow
        v-for="(item, index) in formData.tableData"
        :key="index">
        <WithRelatedClustersColumn
          v-model="item.cluster"
          :cluster-types="[ClusterTypes.TENDBSINGLE]"
          role="orphan"
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <CurrentVersionColumn :cluster="item.cluster" />
        <TargetVersionColumn
          v-model="item.target_version"
          :cluster="item.cluster"
          higher-major-version />
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
          class="ml-8 w-88"
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

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import type { Mysql } from '@services/model/ticket/ticket';

  import { useCreateTicket } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';

  import CurrentVersionColumn from '../components/CurrentVersionColumn.vue';
  import TargetVersionColumn from '../components/TargetVersionColumn.vue';

  interface RowData {
    cluster: {
      bk_cloud_id: number;
      cluster_type: ClusterTypes;
      current_version: string;
      db_module_id: number;
      db_module_name: string;
      id: number;
      master_domain: string;
      package_version: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    };
    target_version: {
      charset: string;
      new_db_module_id: number;
      pkg_id: number;
      target_module_name: string;
      target_package: string;
      target_version: string;
    };
  }

  interface Props {
    ticketDetails?: Mysql.LocalUpgrade;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      bk_cloud_id: 0,
      cluster_type: ClusterTypes.TENDBSINGLE,
      current_version: '',
      db_module_id: 0,
      db_module_name: '',
      id: 0,
      master_domain: '',
      package_version: '',
      related_clusters: [],
    },
    target_version: data.target_version || {
      charset: '',
      new_db_module_id: 0,
      pkg_id: 0,
      target_module_name: '',
      target_package: '',
      target_version: '',
    },
  });

  const defaultData = () => ({
    force: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    formData.tableData
      .filter((item) => item.cluster.id)
      .reduce<Record<string, true>>((acc, cur) => {
        Object.assign(acc, {
          [cur.cluster.master_domain]: true,
        });
        cur.cluster.related_clusters.forEach((item) => {
          Object.assign(acc, {
            [item.master_domain]: true,
          });
        });
        return acc;
      }, {}),
  );

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    force: boolean;
    infos: {
      cluster_ids: number[];
      display_info: {
        charset: string;
        cluster_type: string;
        current_module_name: string;
        current_package: string;
        current_version: string;
        target_module_name: string;
        target_package: string;
        target_version: string;
      };
      new_db_module_id: number;
      pkg_id: number;
    }[];
  }>(TicketTypes.MYSQL_LOCAL_UPGRADE);

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
                bk_cloud_id: clusterInfo.bk_cloud_id,
                cluster_type: clusterInfo.cluster_type,
                current_version: item.display_info.current_version,
                db_module_id: clusterInfo.db_module_id,
                db_module_name: item.display_info.current_module_name,
                id: clusterInfo.id,
                master_domain: clusterInfo.immute_domain,
                package_version: item.display_info.current_package,
                related_clusters: [],
              },
              target_version: {
                charset: item.display_info.charset,
                new_db_module_id: item.new_db_module_id as number,
                pkg_id: item.pkg_id,
                target_module_name: item.display_info.target_module_name as string,
                target_package: item.display_info.target_package,
                target_version: item.display_info.target_version as string,
              },
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: TendbsingleModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              current_version: item.major_version,
              db_module_id: item.db_module_id,
              db_module_name: item.db_module_name,
              id: item.id,
              master_domain: item.master_domain,
              package_version: item.masters[0].version || '',
              related_clusters: [],
            },
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
              charset: item.target_version.charset,
              cluster_type: item.cluster.cluster_type,
              current_module_name: item.cluster.db_module_name,
              current_package: item.cluster.package_version,
              current_version: item.cluster.current_version,
              target_module_name: item.target_version.target_module_name,
              target_package: item.target_version.target_package,
              target_version: item.target_version.target_version,
            },
            new_db_module_id: item.target_version.new_db_module_id,
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
