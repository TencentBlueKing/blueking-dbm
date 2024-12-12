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
    <div class="db-backup-page">
      <BkAlert
        theme="info"
        :title="t('全库备份：所有库表备份, 除 MySQL 系统库和 DBA 专用库外')" />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="tableData"
          :rules="rules">
          <EditableTableRow
            v-for="(item, index) in tableData"
            :key="index">
            <EditClusterColumn
              ref="editClusterColumn"
              v-model="item.cluster"
              @batch-edit="handleClusterBatchEdit" />
            <EditableTableColumn
              field="cluster.cluster_type_name"
              :label="t('集群类型')">
              <EditBlock
                :model-value="item.cluster.cluster_type_name"
                :placeholder="t('输入集群后自动生成')" />
            </EditableTableColumn>
            <OperateColumn
              :removeable="tableData.length < 2"
              show-clone
              @add="() => handleAppend(index)"
              @clone="() => handleClone(index)"
              @remove="() => handleRemove(index)" />
          </EditableTableRow>
        </EditableTable>
        <BkFormItem
          :label="t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup
            v-model="formData.file_tag"
            size="small">
            <BkRadio label="normal_backup">
              {{ t('25天') }}
            </BkRadio>
            <BkRadio label="half_year_backup">
              {{ t('6个月') }}
            </BkRadio>
            <BkRadio label="a_year_backup">
              {{ t('1年') }}
            </BkRadio>
            <BkRadio label="forever_backup">
              {{ t('3年') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('是否备份 Oplog')"
          property="oplog"
          required>
          <BkRadioGroup
            v-model="formData.oplog"
            size="small">
            <BkRadio label="1">
              {{ t('是') }}
            </BkRadio>
            <BkRadio label="0">
              {{ t('否') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <TicketRemark v-model="formData.remark" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';
  import { createTicket } from '@services/source/ticket';

  import { useTicketDetail } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import EditableTable, {
    Block as EditBlock,
    Column as EditableTableColumn,
    Row as EditableTableRow,
  } from '@components/editable-table/Index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import TicketRemark from '@views/db-manage/common/TicketRemark.vue';
  import EditClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-cluster/Index.vue';

  export interface IDataRow {
    cluster: {
      id?: number;
      master_domain?: string;
      cluster_type?: string;
      cluster_type_name?: string;
    };
  }

  const createRowData = (cluster?: IDataRow['cluster']) => ({
    cluster: cluster ? cluster : {},
  });

  const createDefaultFormData = () => ({
    file_tag: 'normal_backup',
    oplog: '0',
    remark: '',
  });

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  useTicketDetail<Mongodb.DbBackupDetails>(TicketTypes.MONGODB_FULL_BACKUP, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters, file_tag: fileTag, oplog } = details;
      tableData.value = infos.map((item) => {
        const clusterItem = clusters[item.cluster_id];
        return createRowData({
          master_domain: clusterItem.immute_domain,
        });
      });
      Object.assign(formData, {
        file_tag: fileTag,
        oplog: oplog ? '1' : '0',
        remark,
      });
    },
  });

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');
  const editClusterColumnRef = useTemplateRef('editClusterColumn');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const nonEmptyIdList = tableData.value.filter((row) => row.cluster.master_domain === value);
            return nonEmptyIdList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('目标集群重复'),
      },
    ],
  };

  const isSubmitting = ref(false);
  const tableData = ref<IDataRow[]>([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList = clusterList.map((item) =>
      createRowData({
        id: item.id,
        master_domain: item.master_domain,
        cluster_type: item.cluster_type,
        cluster_type_name: item.cluster_type_name,
      }),
    );

    tableData.value = [...tableData.value, ...newList];
    window.changeConfirm = true;
  };

  const handleAppend = (index: number) => {
    tableData.value.splice(index + 1, 0, createRowData());
  };

  const handleRemove = (index: number) => {
    const { master_domain: masterDomain, cluster_type: clusterType } = tableData.value[index].cluster;
    tableData.value.splice(index, 1);
    if (clusterType && masterDomain) {
      editClusterColumnRef.value![0]!.setSelectedCluster(clusterType, masterDomain);
    }
  };

  const handleClone = (index: number) => {
    const copyData = _.cloneDeep(tableData.value[index]);
    tableData.value.splice(index + 1, 0, copyData);
    nextTick(() => {
      editableTableRef.value!.validateByRowIndex([index, index + 1]).then();
    });
  };

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      await formRef.value!.validate();
      const validateResult = await editableTableRef.value!.validate();
      if (validateResult) {
        const params = {
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.MONGODB_FULL_BACKUP,
          remark: formData.remark,
          details: {
            file_tag: formData.file_tag,
            oplog: formData.oplog === '1',
            infos: tableData.value.map((tableItem) => ({
              cluster_id: tableItem.cluster.id!,
            })),
          },
        };
        await createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: TicketTypes.MONGODB_FULL_BACKUP,
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        });
      }
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    editClusterColumnRef.value![0]!.resetSelectedCluster();
    tableData.value = [createRowData()];
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .db-backup-page {
    padding-bottom: 20px;
  }
</style>
