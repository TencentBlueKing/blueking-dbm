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
    <div class="sqlserver-db-backup-page">
      <BkAlert
        theme="info"
        :title="t('数据库备份：指定DB备份，支持模糊匹配')" />
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="() => handleRemove(index)" />
      </RenderData>
      <DbForm
        class="db-backup-form mt16"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('备份方式')"
          property="backup_type"
          required>
          <BkRadioGroup
            v-model="formData.backup_type"
            size="small">
            <BkRadio label="full_backup">
              {{ t('全量备份') }}
            </BkRadio>
            <BkRadio label="log_backup">
              {{ t('增量备份') }}
            </BkRadio>
          </BkRadioGroup>
        </BkFormItem>
        <BkFormItem
          :label="t('备份位置')"
          property="backup_place"
          required>
          <BkSelect
            v-model="formData.backup_place"
            disabled
            :list="backupLocationList"
            style="width: 360px" />
        </BkFormItem>
        <BkFormItem
          :label="t('备份保存时间')"
          property="file_tag"
          required>
          <BkRadioGroup
            v-model="formData.file_tag"
            size="small">
            <template v-if="isBackupTypeFull">
              <BkRadio label="DBFILE1M"> {{ t('1 个月') }} </BkRadio>
              <BkRadio label="DBFILE6M"> {{ t('6 个月') }} </BkRadio>
              <BkRadio label="DBFILE1Y"> {{ t('1 年') }} </BkRadio>
              <BkRadio label="DBFILE3Y"> {{ t('3 年') }} </BkRadio>
            </template>
            <template v-else>
              <BkRadio label="INCREMENT_BACKUP"> 15 {{ t('天') }} </BkRadio>
            </template>
          </BkRadioGroup>
        </BkFormItem>
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
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderRow, { createRowData, type IDataRow } from './components/RenderData/RenderRow.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const backupLocationList = [
    {
      value: 'master',
      label: t('主库主机'),
    },
  ];

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_SINGLE]: {
      name: t('单节点集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      name: t('主从集群'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const createDefaultData = () => ({
    backup_type: 'full_backup',
    backup_place: 'master',
    file_tag: 'DBFILE1M',
  });

  const rowRefs = ref<InstanceType<typeof RenderRow>[]>();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<IDataRow[]>([createRowData()]);
  const formData = reactive(createDefaultData());

  const selectedClusters = shallowRef<{ [key: string]: (SqlServerSingleModel | SqlServerHaModel)[] }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const isBackupTypeFull = computed(() => formData.backup_type === 'full_backup');

  useTicketCloneInfo({
    type: TicketTypes.SQLSERVER_BACKUP_DBS,
    onSuccess(cloneData) {
      formData.backup_type = cloneData.backup_type;
      formData.backup_place = cloneData.backup_place;
      formData.file_tag = cloneData.file_tag;
      tableData.value = cloneData.info.map((item) =>
        createRowData({
          clusterData: {
            id: item.cluster.id,
            domain: item.cluster.immute_domain,
            cloudId: item.cluster.bk_cloud_id,
          },
          dbList: item.db_list,
          ignoreDbList: item.ignore_db_list,
        }),
      );
    },
  });

  watch(
    () => formData.backup_type,
    () => {
      formData.file_tag = isBackupTypeFull.value ? 'DBFILE1M' : 'INCREMENT_BACKUP';
    },
  );

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 输入集群后查询集群信息并填充到table
  // 批量选择
  const handelClusterChange = (selected: { [key: string]: Array<SqlServerSingleModel | SqlServerHaModel> }) => {
    selectedClusters.value = selected;
    const list = _.flatten(Object.values(selected));
    const newList = list.reduce((result, item) => {
      const row = createRowData({
        clusterData: {
          id: item.id,
          domain: item.master_domain,
          cloudId: item.bk_cloud_id,
        },
      });
      result.push(row);
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = async () => {
    isSubmitting.value = true;
    try {
      const infos = await Promise.all(rowRefs.value!.map((item) => item.getValue()));
      await createTicket({
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.SQLSERVER_BACKUP_DBS,
        details: {
          ...formData,
          infos,
        },
      }).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'SqlServerDbBackup',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    Object.assign(formData, createDefaultData());
    selectedClusters.value = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
    };
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .sqlserver-db-backup-page {
    padding-bottom: 20px;

    .bk-form-label {
      font-size: 12px;
      font-weight: bold;
    }
  }
</style>
