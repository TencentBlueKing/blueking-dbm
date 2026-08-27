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
  <BkFormItem
    :label="t('新机所需数据')"
    required>
    <BkRadioGroup
      v-model="formData.orphan_restore_type"
      @change="handleChange">
      <BkRadio label="restore_with_data">
        {{ t('包含数据') }}
      </BkRadio>
      <BkRadio label="restore_with_struct">
        {{ t('仅表结构(最近1次远程备份)') }}
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
  <BatchInput
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
    ref="table"
    class="mt-16 mb-20"
    :model="formData.tableData">
    <EditableRow
      v-for="(item, index) in formData.tableData"
      :key="index">
      <HostColumnGroup
        v-model="item.host"
        :selected="selected"
        :selected-map="selectedMap"
        @batch-edit="handleBatchEditHost" />
      <SpecColumn
        v-model="item.specId"
        :cluster-type="DBTypes.MYSQL"
        :current-spec-id-list="[item.host.spec.id]"
        required
        selectable
        @batch-edit="handleBatchEdit" />
      <ResourceTagColumn
        v-model="item.labels"
        @batch-edit="handleBatchEdit" />
      <AvailableResourceColumn
        :params="{
          city: item.host.city,
          subzones: item.host.subzones,
          for_bizs: [currentBizId, 0],
          resource_types: [DBTypes.MYSQL, 'PUBLIC'],
          spec_id: item.specId,
          labels: item.labels.map((item) => item.id).join(','),
        }" />
      <OperationColumn
        v-model:table-data="formData.tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
  <TicketPayload v-model="formData.payload" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { type Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useTicketDetail } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTicketPayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorHost } from '../components/HostColumnGroup.vue';

  interface RowData {
    host: ComponentProps<typeof HostColumnGroup>['modelValue'];
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
    },
    {
      case: '2核_4G_50G',
      key: 'spec_name',
      label: t('目标规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    host: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        city: '',
        ip: '',
        related_instances: [],
        spec: {
          id: 0,
        },
        subzones: '',
      } as unknown as RowData['host'],
      data.host,
    ),
    labels: (data.labels || []) as RowData['labels'],
    specId: data.specId || 0,
  });

  const formData = reactive({
    backup_source: BackupSourceType.REMOTE, // 固定传remote, 页面不展示
    orphan_restore_type: 'restore_with_data',
    payload: createTicketPayload(),
    tableData: [createTableRow()],
  });
  const tableKey = ref(random());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mysql.ResourcePool.MigrateSingle>(TicketTypes.MYSQL_MIGRATE_SINGLE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      if (details.migrate_type !== 'failover') {
        return;
      }
      Object.assign(formData, {
        backup_source: details.backup_source,
        orphan_restore_type: details.orphan_restore_type,
        payload: createTicketPayload(ticketDetail),
        tableData: details.infos.map((item) =>
          createTableRow({
            host: {
              ip: item.old_orphan.ip,
            },
            labels: (item.resource_spec.bk_new_orphan?.labels || []).map((item) => ({ id: Number(item) })),
            specId: item.resource_spec.bk_new_orphan?.spec_id || 0,
          }),
        ),
      });
    },
  });

  const handleChange = (value: string) => {
    formData.orphan_restore_type = value;
    formData.backup_source = BackupSourceType.LOCAL;
  };

  const handleBatchEditHost = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            host: {
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: _.cloneDeep(value),
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          host: {
            ip: item.ip,
          },
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...formData.tableData.filter((item) => item.host.ip), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  defineExpose({
    getValue() {
      return tableRef.value!.validate().then(() => {
        return {
          details: {
            backup_source: formData.backup_source,
            infos: formData.tableData.map((item) => ({
              cluster_ids: item.host.related_instances.map((instance) => instance.cluster_id),
              old_orphan: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: item.host.bk_cloud_id,
                bk_host_id: item.host.bk_host_id,
                ip: item.host.ip,
              },
              related_cluster_infos: item.host.related_instances.map((instance) => ({
                cluster_id: instance.cluster_id,
                instance_address: instance.instance_address,
                master_domain: instance.master_domain,
              })),
              resource_spec: {
                bk_new_orphan: {
                  count: 1,
                  label_names: item.labels.map((item) => item.value),
                  labels: item.labels.map((item) => String(item.id)),
                  spec_id: item.specId,
                },
              },
            })),
            ip_source: 'resource_pool',
            migrate_type: 'failover',
            orphan_restore_type: formData.orphan_restore_type,
          },
          ...formData.payload,
        };
      });
    },
  });
</script>
