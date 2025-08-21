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
    <BkAlert
      class="mb-20"
      closable
      :title="t('重建从库_原机器或新机器重新同步数据及权限_并且将域名解析指向同步好的机器')" />
    <div class="title-spot mt-12 mb-10">{{ t('重建类型') }}<span class="required" /></div>
    <div class="mt-8 mb-20">
      <CardCheckbox
        v-model="restoreType"
        :desc="t('在原主机上进行故障从库实例重建')"
        icon="rebuild"
        :title="t('原地重建')"
        :true-value="TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE" />
      <CardCheckbox
        v-model="restoreType"
        class="ml-8"
        :desc="t('将从库主机的全部实例重建到新主机')"
        icon="host"
        :title="t('新机重建')"
        :true-value="TicketTypes.MYSQL_RESTORE_SLAVE" />
    </div>
    <BkForm
      class="mb-20"
      form-type="vertical"
      :model="formData">
      <!-- <div class="title-spot mt-12 mb-10">{{ t('主机选择方式') }}<span class="required" /></div>
      <BkRadioGroup
        v-model="sourceType"
        class="mb-16"
        style="width: 450px"
        type="card"
        @change="handleChangeMode">
        <BkRadioButton :label="SourceType.RESOURCE_AUTO">
          {{ t('资源池自动匹配') }}
        </BkRadioButton>
        <BkRadioButton :label="SourceType.RESOURCE_MANUAL">
          {{ t('资源池手动选择') }}
        </BkRadioButton>
      </BkRadioGroup> -->
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
          <SlaveHostColumnGroup
            v-model="item.slave"
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <template v-if="sourceType === SourceType.RESOURCE_AUTO">
            <SpecColumn
              v-model="item.specId"
              :cluster-type="DBTypes.MYSQL"
              :current-spec-id-list="[item.slave.spec_id]"
              required />
            <ResourceTagColumn
              v-model="item.labels"
              @batch-edit="handleBatchEditColumn" />
            <AvailableResourceColumn
              :params="{
                city: item.slave.bk_idc_city_name,
                subzones: item.slave.bk_sub_zone,
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MYSQL, 'PUBLIC'],
                spec_id: item.specId,
                labels: item.labels.map((item) => item.id).join(','),
              }" />
          </template>
          <template v-if="sourceType === SourceType.RESOURCE_MANUAL">
            <SingleResourceHostColumn
              v-model="item.newSlave"
              field="newSlave.ip"
              :label="t('新从库主机')"
              :min-width="150"
              :params="{
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.MYSQL, 'PUBLIC'],
              }" />
          </template>
          <OperationColumn
            v-model:table-data="formData.tableData"
            :create-row-method="createTableRow" />
        </EditableRow>
      </EditableTable>
      <BkFormItem
        :label="t('备份源')"
        property="backupSource"
        required>
        <BkRadioGroup v-model="formData.backupSource">
          <BkRadio :label="BackupSourceType.LOCAL">
            {{ t('本地备份（Master）') }}
          </BkRadio>
          <BkRadio :label="BackupSourceType.REMOTE">
            {{ t('远程备份') }}
          </BkRadio>
        </BkRadioGroup>
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { type Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType, SourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import CardCheckbox from '@components/db-card-checkbox/CardCheckbox.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import { random } from '@utils';

  import SlaveHostColumnGroup, { type SelectorHost } from './components/SlaveHostColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    newSlave: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
    slave: ComponentProps<typeof SlaveHostColumnGroup>['modelValue'];
    specId: number;
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');
  const router = useRouter();
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    labels: (data.labels || []) as RowData['labels'],
    newSlave: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.newSlave,
    ),
    slave: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_idc_city_name: '',
        bk_sub_zone: '',
        ip: '',
        related_clusters: [] as RowData['slave']['related_clusters'],
        role: '',
        spec_id: 0,
      },
      data.slave,
    ),
    specId: data.specId || 0,
  });

  const defaultData = () => ({
    backupSource: BackupSourceType.REMOTE,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const restoreType = ref<TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE | TicketTypes.MYSQL_RESTORE_SLAVE>(
    TicketTypes.MYSQL_RESTORE_SLAVE,
  );
  const sourceType = ref(SourceType.RESOURCE_AUTO);
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  const batchInputConfig = computed(() => {
    if (sourceType.value === SourceType.RESOURCE_AUTO) {
      return [
        {
          case: '192.168.10.2',
          key: 'slave_ip',
          label: t('目标从库主机'),
        },
        {
          case: '标签1,标签2',
          key: 'labels',
          label: t('资源标签'),
        },
      ];
    }
    return [
      {
        case: '192.168.10.2',
        key: 'slave_ip',
        label: t('目标从库主机'),
      },
      {
        case: '192.168.10.2',
        key: 'new_slave_ip',
        label: t('新从库主机'),
      },
    ];
  });

  const selected = computed(() => formData.tableData.filter((item) => item.slave.bk_host_id).map((item) => item.slave));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  useTicketDetail<Mysql.ResourcePool.RestoreSlave>(TicketTypes.MYSQL_RESTORE_SLAVE, {
    onSuccess(ticketDetail) {
      const { backup_source: backupSource, infos } = ticketDetail.details;
      sourceType.value = ticketDetail.details.source_type;
      tableKey.value = random();
      Object.assign(formData, {
        backupSource,
        ...createTickePayload(ticketDetail),
        tableData: infos.map((item) =>
          createTableRow({
            labels: (item.resource_spec.new_slave.labels || []).map((item) => ({ id: Number(item) })),
            newSlave: item.resource_spec.new_slave.hosts?.[0],
            slave: {
              ip: item.old_nodes.old_slave?.[0]?.ip || '',
            },
            specId: item.resource_spec.new_slave.spec_id,
          }),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: BackupSourceType;
    infos: {
      cluster_ids: number[];
      old_nodes: {
        old_slave: RowData['newSlave'][];
      };
      resource_spec: {
        new_slave: {
          count: number;
          hosts?: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          }[];
          label_names?: string[]; // 标签名称列表，单据详情回显用
          labels?: string[]; // 标签id列表
          spec_id: number;
        };
      };
    }[];
    ip_source: 'resource_pool';
    source_type: SourceType;
  }>(TicketTypes.MYSQL_RESTORE_SLAVE);

  watch(restoreType, () => {
    if (restoreType.value === TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE) {
      router.push({
        name: TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
      });
    }
  });

  // const handleChangeMode = () => {
  //   tableKey.value = random();
  // };

  const handleSubmit = async () => {
    const valid = await tableRef.value!.validate();
    if (valid) {
      createTicketRun({
        details: {
          backup_source: formData.backupSource,
          infos: formData.tableData.map((item) => ({
            cluster_ids: item.slave.related_clusters.map((item) => item.id),
            old_nodes: {
              old_slave: [
                {
                  bk_biz_id: item.slave.bk_biz_id,
                  bk_cloud_id: item.slave.bk_cloud_id,
                  bk_host_id: item.slave.bk_host_id,
                  ip: item.slave.ip,
                },
              ],
            },
            resource_spec: {
              new_slave: {
                count: 1,
                hosts: sourceType.value === SourceType.RESOURCE_MANUAL ? [item.newSlave] : undefined,
                label_names:
                  sourceType.value === SourceType.RESOURCE_AUTO ? item.labels.map((item) => item.value) : undefined,
                labels:
                  sourceType.value === SourceType.RESOURCE_AUTO
                    ? item.labels.map((item) => String(item.id))
                    : undefined,
                spec_id: item.slave.spec_id,
              },
            },
          })),
          ip_source: 'resource_pool',
          source_type: sourceType.value,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };

  const handleBatchEdit = (list: SelectorHost[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            slave: {
              ip: item.ip,
            },
            specId: item.spec_config.id,
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          newSlave: {
            ip: item.new_slave_ip,
          },
          slave: {
            ip: item.slave_ip,
          },
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.tableData.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };
</script>
