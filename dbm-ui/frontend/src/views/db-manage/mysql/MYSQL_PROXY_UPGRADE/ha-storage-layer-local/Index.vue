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
  <SmartAction>
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
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <CurrentVersionColumn :cluster="item.cluster" />
        <TargetVersionColumn
          v-model="item.target_version"
          :cluster="item.cluster" />
        <OperationColumn
          v-model:table-data="formData.tableData"
          :create-row-method="createTableRow" />
      </EditableRow>
    </EditableTable>
    <IgnoreBiz
      v-model="formData.force"
      v-bk-tooltips="t('如忽略_有连接的情况下也会执行')" />
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

  import { TicketTypes } from '@common/const';

  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';

  import CurrentVersionColumn from '../components/CurrentVersionColumn.vue';

  import TargetVersionColumn from './components/TargetVersionColumn.vue';

  interface RowData {
    cluster: {
      bk_cloud_id: number;
      cluster_type: string;
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
      pkg_id: number;
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
      cluster_type: '',
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
      pkg_id: 0,
      target_package: '',
      target_version: '',
    },
  });

  const defaultData = () => ({
    force: false,
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
        charset: string;
        cluster_type: string;
        current_module_name: string;
        current_package: string;
        current_version: string;
        target_package: string;
        target_version: string;
      };
      pkg_id: number;
    }[];
  }>(TicketTypes.MYSQL_LOCAL_UPGRADE, {
    ticketTypeRoute: TicketTypes.MYSQL_PROXY_UPGRADE,
  });

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
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
                pkg_id: item.pkg_id,
                target_package: item.display_info.target_package,
                target_version: item.display_info.target_version as string,
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
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              current_version: item.major_version,
              db_module_id: item.db_module_id,
              db_module_name: item.db_module_name,
              id: item.id,
              master_domain: item.master_domain,
              package_version: item.masters[0]?.version || '',
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
              target_package: item.target_version.target_package,
              target_version: item.target_version.target_version,
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
