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
    <div class="mongo-db-table-backup-page">
      <BkAlert
        closable
        theme="info"
        :title="t('库表备份：指定库表备份，支持模糊匹配')" />
      <div class="title-spot mt-12 mb-10">{{ t('集群类型') }}<span class="required" /></div>
      <BkRadioGroup
        v-model="clusterType"
        style="width: 400px"
        type="card">
        <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
          {{ t('副本集集群') }}
        </BkRadioButton>
        <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
          {{ t('分片集群') }}
        </BkRadioButton>
      </BkRadioGroup>
      <template v-if="isShardCluster">
        <div class="title-spot mt-12 mb-10">{{ t('备份位置') }}<span class="required" /></div>
        <BkRadioGroup
          v-model="backupType"
          style="width: 400px"
          type="card">
          <BkRadioButton label="shard"> Shard </BkRadioButton>
          <BkRadioButton label="mongos"> Mongs </BkRadioButton>
        </BkRadioGroup>
      </template>
      <RenderData
        :key="`${clusterType}_${backupType}`"
        :backup-type="backupType"
        class="mt16"
        :is-shard-cluster="isShardCluster"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :backup-type="backupType"
          :cluster-type="clusterType"
          :data="item"
          :is-shard-cluster="isShardCluster"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <DbForm
        ref="formRef"
        class="db-table-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <BkFormItem
          :label="t('备份文件保存时间')"
          property="file_tag">
          <BkRadioGroup
            v-model="formData.file_tag"
            size="small">
            <BkRadio label="normal_backup">
              {{ t('常规备份（25天）') }}
            </BkRadio>
            <BkRadio label="forever_backup">
              {{ t('长期备份（3年）') }}
            </BkRadio>
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </SmartAction>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting  = ref(false);
  const clusterType = ref(ClusterTypes.MONGO_REPLICA_SET);
  const backupType = ref('shard');
  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const selectedClusters = shallowRef<{[key: string]: Array<MongodbModel>}>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const formData = reactive({
    file_tag: 'normal_backup',
  });

  const isShardCluster = computed(() => clusterType.value === ClusterTypes.MONGO_SHARED_CLUSTER);

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData
      && !firstRow.dbPatterns
      && !firstRow.ignoreDbs
      && !firstRow.tablePatterns
      && !firstRow.ignoreTables;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<MongodbModel>}) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.MONGO_SHARED_CLUSTER];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = {
          clusterData: {
            id: item.id,
            domain: item.master_domain,
          },
          rowData: item,
        } as IDataRow;
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    if (!domain) {
      const { clusterData } = tableData.value[index];
      const clusterName = clusterData?.domain
      if (clusterName) {
        domainMemo[clusterName] = false;
        delete tableData.value[index].clusterData;
      }
      return;
    }
    const result = await getMongoList({ exact_domain: domain })
    if (result.results.length < 1) {
      return;
    }
    const item = result.results[0];
    const row = {
      clusterData: {
        id: item.id,
        domain: item.master_domain,
      },
      rowData: item,
    } as IDataRow;
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER].push(item);
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
    const domain = dataList[index].clusterData?.domain;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER];
      selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = clustersArr.filter(item => item.master_domain !== domain);
    }
  };

  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));

    const params: Record<string, any> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_BACKUP,
      remark: '',
      details: {
        file_tag: formData.file_tag,
        backup_type: backupType.value,
        infos,
      },
    };
    if (clusterType.value === ClusterTypes.MONGO_REPLICA_SET) {
      delete params.details.backup_type;
    }

    InfoBox({
      title: t('确认提交n个库表备份任务', { n: infos.length }),
      subTitle: t('将会对库表进行备份'),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MongoDbTableBackup',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mongo-db-table-backup-page {
    padding-bottom: 20px;

    .title-spot {
      font-weight: normal;
    }

    .db-table-form {
      .bk-form-label {
        font-size: 12px;
      }
    }
  }
</style>
