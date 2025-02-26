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
      :model="formData.tableData">
      <EditableRow
        v-for="(item, index) in formData.tableData"
        :key="index">
        <HaClusterColumn
          v-model="item.cluster"
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <EditableColumn
          field="cluster.current_version"
          :label="t('当前版本')"
          :min-width="200"
          required>
          <EditableBlock
            v-model="item.cluster.current_version"
            :placeholder="t('自动生成')" />
        </EditableColumn>
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
    <TicketPayload v-model="formData" />
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

  import { useCreateTicket } from '@hooks';

  import { TicketTypes } from '@common/const';

  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import HaClusterColumn from '../components/HaClusterColumn.vue';

  import TargetVersionColumn from './components/TargetVersionColumn.vue';

  interface RowData {
    cluster: {
      current_version: string;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    };
    target_version: {
      pkg_id: number;
      target_package: string;
    };
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      current_version: '',
      id: 0,
      master_domain: '',
      related_clusters: [],
    },
    target_version: data.target_version || {
      pkg_id: 0,
      target_package: '',
    },
  });

  const defaultData = () => ({
    force: false,
    tableData: [createTableRow()],
    ...createTickePayload(),
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() =>
    formData.tableData
      .filter((item) => item.cluster.id)
      .reduce<Record<string, true>>((acc, cur) => {
        // eslint-disable-next-line no-param-reassign
        acc[cur.cluster.master_domain] = true;
        cur.cluster.related_clusters.forEach((item) => {
          // eslint-disable-next-line no-param-reassign
          acc[item.master_domain] = true;
        });
        return acc;
      }, {}),
  );

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              current_version: item.proxies[0]?.version || '',
              id: item.id,
              master_domain: item.master_domain,
              related_clusters: [],
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
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

  const handleSubmit = async () => {
    const result = await tableRef.value?.validate();
    if (result) {
      createTicketRun({
        details: {
          force: formData.force,
          infos: formData.tableData.map((item) => ({
            cluster_ids: [item.cluster.id],
            display_info: {
              current_version: item.cluster.current_version,
              target_package: item.target_version.target_package,
            },
            pkg_id: item.target_version.pkg_id,
          })),
        },
        remark: formData.remark,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
