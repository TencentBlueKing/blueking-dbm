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
  <div class="redis-cluster-rollback-data-copy-page">
    <SmartAction>
      <BkAlert
        class="mb-16"
        closable
        theme="info"
        :title="t('以构造实例恢复：把构造实例上的数据写回原集群')" />
      <BatchInput
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <DbForm
        ref="form"
        class="mt-16 mb-24 toolbox-form"
        form-type="vertical"
        :model="formData">
        <EditableTable
          :key="tableKey"
          ref="editableTable"
          class="mb-24"
          :model="formData.tableData">
          <EditableRow
            v-for="(rowData, index) in formData.tableData"
            :key="index">
            <SourceClusterColumn
              v-model="rowData.cluster"
              :selected="selected"
              @batch-edit="handleClusterBatchEdit" />
            <EditableColumn
              :label="t('目标集群')"
              readonly
              :width="200">
              <EditableBlock
                v-model="rowData.cluster.prod_cluster"
                :placeholder="t('自动生成')">
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('构造到指定时间')"
              readonly
              :width="200">
              <EditableBlock
                v-model="rowData.cluster.recovery_time_point"
                :placeholder="t('自动生成')">
              </EditableBlock>
            </EditableColumn>
            <RegexKeysColumn
              v-model="rowData.key_white_regex"
              field="key_white_regex"
              :label="t('包含 Key')"
              required
              @batch-edit="handleBatchEdit">
            </RegexKeysColumn>
            <RegexKeysColumn
              v-model="rowData.key_black_regex"
              field="key_black_regex"
              :label="t('排除 Key')"
              @batch-edit="handleBatchEdit">
            </RegexKeysColumn>
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <BkFormItem
          :label="t('写入类型')"
          property="write_mode"
          required>
          <BkRadioGroup v-model="formData.write_mode">
            <BkRadio
              v-for="item in writeTypeList"
              :key="item.value"
              :label="item.value">
              {{ item.label }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
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
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { WriteModes } from '@services/model/redis/redis-dst-history-job';
  import RedisRollbackModel from '@services/model/redis/redis-rollback';
  import { type Redis } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import RegexKeysColumn from '@views/db-manage/redis/common/toolbox-field/regex-keys-column/Index.vue';

  import { random } from '@utils';

  import SourceClusterColumn from './components/SourceClusterColumn.vue';

  interface IDataRow {
    cluster: RedisRollbackModel;
    key_black_regex: string[];
    key_white_regex: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    // 只初始化需要的字段
    cluster: Object.assign(
      {
        id: 0,
        prod_cluster: '',
        prod_cluster_id: 0,
        recovery_time_point: '',
        temp_cluster_proxy: '',
      },
      values.cluster,
    ),
    key_black_regex: values?.key_black_regex || [],
    key_white_regex: values?.key_white_regex || [],
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
    write_mode: WriteModes.DELETE_AND_WRITE_TO_REDIS,
  });

  const { t } = useI18n();
  const route = useRoute();

  useTicketDetail<Redis.ClusterRollbackDataCopy>(TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: details.infos.map((infoItem) =>
          createRowData({
            cluster: {
              temp_cluster_proxy: infoItem.src_cluster,
            } as IDataRow['cluster'],
            key_black_regex: infoItem.key_black_regex.split('\n'),
            key_white_regex: infoItem.key_white_regex.split('\n'),
          }),
        ),
        write_mode: details.write_mode,
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    //  dts 复制类型: 回档临时实例数据回写
    dts_copy_type: 'copy_from_rollback_instance';
    infos: {
      dst_cluster: number;
      key_black_regex: string; // 排除key
      key_white_regex: string; // 包含key
      recovery_time_point: string; // 构造到指定时间
      src_cluster: string; // 构造产物访问入口
    }[];
    write_mode: string;
  }>(TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY);

  const batchInputConfig = [
    {
      case: 'redis.test.dba.db:10000',
      key: 'temp_cluster_proxy',
      label: t('构造产物访问入口'),
    },
    {
      case: 'key1,key2',
      key: 'key_white_regex',
      label: t('包含 Key'),
    },
    {
      case: 'key1,key2',
      key: 'key_black_regex',
      label: t('排除 Key'),
    },
  ];

  const writeTypeList = [
    {
      label: t('先删除同名 Key，再写入（如：del  $key+ hset $key）'),
      value: WriteModes.DELETE_AND_WRITE_TO_REDIS,
    },
    {
      label: t('保留同名 Key，追加写入（如：hset $key）'),
      value: WriteModes.KEEP_AND_APPEND_TO_REDIS,
    },
    {
      label: t('清空目标集群所有数据，再写入'),
      value: WriteModes.FLUSHALL_AND_WRITE_TO_REDIS,
    },
  ];

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const tableKey = ref(random());

  const formData = reactive(createDefaultFormData());

  const selected = computed(() =>
    formData.tableData.filter((item) => item.cluster.temp_cluster_proxy).map((item) => item.cluster),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.temp_cluster_proxy, true])));

  const { domains } = route.query as { domains: string };
  if (domains) {
    formData.tableData = domains.split(',').map((domain) =>
      createRowData({
        cluster: {
          temp_cluster_proxy: domain,
        } as IDataRow['cluster'],
      }),
    );
  }

  const handleClusterBatchEdit = (clusterList: RedisRollbackModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.temp_cluster_proxy]) {
        newList.push(
          createRowData({
            cluster: item,
          }),
        );
      }
    });
    formData.tableData = [...(formData.tableData[0].cluster.temp_cluster_proxy ? formData.tableData : []), ...newList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          cluster: {
            temp_cluster_proxy: item.temp_cluster_proxy,
          } as IDataRow['cluster'],
          key_black_regex: item.key_black_regex ? item.key_black_regex.split(',') : [],
          key_white_regex: item.key_white_regex ? item.key_white_regex.split(',') : [],
        }),
      );
      return acc;
    }, []);

    if (isClear) {
      tableKey.value = random();
      formData.tableData = [...dataList];
    } else {
      formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
    }

    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleBatchEdit = (value: string[], field: string) => {
    formData.tableData.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          dts_copy_type: 'copy_from_rollback_instance',
          infos: formData.tableData.map((row) => ({
            dst_cluster: row.cluster.prod_cluster_id,
            key_black_regex: row.key_black_regex.join('\n'),
            key_white_regex: row.key_white_regex.join('\n'),
            recovery_time_point: row.cluster.recovery_time_point,
            src_cluster: row.cluster.temp_cluster_proxy,
          })),
          write_mode: formData.write_mode,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
  };
</script>

<style lang="less">
  .redis-cluster-rollback-data-copy-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
