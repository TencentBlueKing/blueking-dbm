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
    <div class="mongodb-shard-migrate-page db-toolbox">
      <BkAlert
        closable
        theme="info"
        :title="t('迁移：将指定副本集、分片迁移至新机器')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <MigrateFormItem v-model="formData.architectureType" />
        <BatchInput
          :config="batchInputConfig"
          @change="handleBatchInput" />
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mt-16 mb-16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <ShardNameBatchColumn
              v-model="item.batchShard"
              :selected="selected"
              :selected-map="selectedMap"
              @batch-edit="handleShardNameBatchEdit" />
            <RelatedInstanceColumn :shards="item.batchShard.shards" />
            <SpecColumn
              v-model="item.target_spec_id"
              :cluster-type="DBTypes.MONGODB"
              :current-spec-id-list="[item.batchShard.current_spec_id]"
              field="target_spec_id"
              label="目标规格"
              :machine-type="MachineTypes.MONGODB"
              required
              selectable
              @batch-edit="handleBatchEdit" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
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

<script setup lang="tsx">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mongodb } from '@services/model/ticket/ticket';
  import { getMongoShard } from '@services/source/mongodbToolbox';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import MigrateFormItem from '@views/db-manage/mongodb/common/migrate-form-item/Index.vue';

  import { random } from '@utils';

  import RelatedInstanceColumn, { getClusterInstanceList } from './components/RelatedInstanceColumn.vue';
  import ShardNameBatchColumn from './components/ShardNameBatchColumn.vue';

  interface IDataRow {
    batchShard: ComponentProps<typeof ShardNameBatchColumn>['modelValue'];
    target_spec_id: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    batchShard: Object.assign(
      {
        renderText: '',
        shards: {} as IDataRow['batchShard']['shards'],
      },
      values.batchShard,
    ),
    target_spec_id: values.target_spec_id || 0,
  });

  const createDefaultFormData = () => ({
    architectureType: TicketTypes.MONGODB_SHARD_MIGRATE,
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Mongodb.ShardMigrate>(TicketTypes.MONGODB_SHARD_MIGRATE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;

      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.map((item) => {
          return createRowData({
            batchShard: {
              renderText: item.shard_name.join('\n'),
            } as IDataRow['batchShard'],
            target_spec_id: item.resource_spec.mongodb.spec_id,
          });
        }),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      city_code: string;
      cluster_id: number;
      current_shard_nodes_num: number; // 当前每分片节点数
      db_version: string;
      disaster_tolerance_level: string;
      old_nodes: {
        shard: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      related_instances: {
        domain: string;
        instances: string[];
      }[]; // 展示用
      resource_spec: {
        mongodb: {
          count: number;
          spec_id: number;
        };
      };
      shard_name: string[];
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MONGODB_SHARD_MIGRATE);

  const batchInputConfig = [
    {
      case: 'shard-name1\\nshard-name2',
      key: 'shard_name',
      label: t('目标分片'),
    },
    {
      case: t('无限制'),
      key: 'spec_name',
      label: t('目标规格'),
    },
  ];

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() =>
    formData.tableData
      .filter((item) => item.batchShard.renderText)
      .flatMap((item) => Object.values(item.batchShard.shards)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.shard_name, true])));

  const handleShardNameBatchEdit = (shardList: ServiceReturnType<typeof getMongoShard>['results']) => {
    const newList: IDataRow[] = [];
    shardList.forEach((item) => {
      if (!selectedMap.value[item.shard_name]) {
        newList.push(
          createRowData({
            batchShard: {
              renderText: item.shard_name,
            } as IDataRow['batchShard'],
          }),
        );
      }
    });

    formData.tableData = [...formData.tableData.filter((item) => item.batchShard.renderText), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchEdit = (value: number, field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          batchShard: {
            renderText: item.shard_name?.replaceAll('\\n', '\n') || '',
          } as IDataRow['batchShard'],
          target_spec_id: item.spec_name,
        }),
      );
      return acc;
    }, []);

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...newList];
    } else {
      formData.tableData = [...formData.tableData.filter((item) => item.batchShard.renderText), ...newList];
    }

    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: formData.tableData.map((tableItem) => {
            // 取首个分片信息，给定校验基准
            const shardInfo = Object.values(tableItem.batchShard.shards)[0];
            const oldNodes = _.uniqBy(
              Object.values(tableItem.batchShard.shards).flatMap((shardItem) =>
                shardItem.related_instance.map((instanceItem) => ({
                  bk_biz_id: instanceItem.bk_biz_id,
                  bk_cloud_id: instanceItem.bk_cloud_id,
                  bk_host_id: instanceItem.bk_host_id,
                  ip: instanceItem.ip,
                })),
              ),
              'bk_host_id',
            );
            return {
              city_code: shardInfo.region,
              cluster_id: shardInfo.cluster_id,
              current_shard_nodes_num: shardInfo.shard_node_count,
              db_version: shardInfo.major_version,
              disaster_tolerance_level: shardInfo.disaster_tolerance_level,
              old_nodes: {
                shard: oldNodes,
              },
              related_instances: getClusterInstanceList(tableItem.batchShard.shards),
              resource_spec: {
                mongodb: {
                  count: 1 * shardInfo.shard_node_count, // 迁移到同一组
                  spec_id: tableItem.target_spec_id,
                },
              },
              shard_name: Object.values(tableItem.batchShard.shards).map((item) => item.shard_name),
            };
          }),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .mongodb-shard-migrate-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
