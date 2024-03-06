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
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="() => handleAppend(index)"
          @input-cluster-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="() => handleRemove(index)" />
      </RenderData>
      <DbForm
        ref="formRef"
        class="db-backup-form"
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
        <BkFormItem
          :label="t('是否开启 Oplog')"
          property="oplog">
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
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGO_REPLICA_SET]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const createDefaultData = () => ({
    file_tag: 'normal_backup',
    oplog: '0',
  });

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const formRef = ref();
  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const formData = reactive(createDefaultData());

  const tableData = ref<IDataRow[]>([createRowData()]);
  const selectedClusters = shallowRef<{ [key: string]: MongodbModel[] }>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    [ClusterTypes.MONGO_REPLICA_SET]: [],
  });

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.clusterName)).length);

  const tabListConfig = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterName;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: MongodbModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    clusterName: item.master_domain,
    clusterId: item.id,
    clusterTypeText: item.clusterTypeText,
    clusterType: item.cluster_type,
  });

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: MongodbModel[] }) => {
    selectedClusters.value = selected;
    let list: MongodbModel[] = [];
    if (selected[ClusterTypes.MONGO_REPLICA_SET]) {
      list = selected[ClusterTypes.MONGO_REPLICA_SET];
    }
    if (selected[ClusterTypes.MONGO_SHARED_CLUSTER]) {
      list = [...list, ...selected[ClusterTypes.MONGO_SHARED_CLUSTER]];
    }
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
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
      const { clusterName } = tableData.value[index];
      domainMemo[clusterName] = false;
      tableData.value[index].clusterName = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await getMongoList({ exact_domain: domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length < 1) {
      return;
    }
    const item = result.results[0];
    const row = generateRowDateFromRequest(item);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[item.cluster_type].push(item);
  };

  // 追加集群
  const handleAppend = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, createRowData());
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const {
      clusterName,
      clusterType,
    } = dataList[index];
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (clusterName) {
      delete domainMemo[clusterName];
      const clustersArr = selectedClusters.value[clusterType];
      selectedClusters.value[clusterType] = clustersArr.filter((item) => item.master_domain !== clusterName);
    }
  };

  const handleSubmit = async () => {
    const infos = await Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));

    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_FULL_BACKUP,
      remark: '',
      details: {
        file_tag: formData.file_tag,
        oplog: formData.oplog === '1',
        infos,
      },
    };

    InfoBox({
      title: t('确认提交n个全库备份任务', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params)
          .then((data) => {
            window.changeConfirm = false;
            router.push({
              name: 'MongoDbBackup',
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
      },
    });
  };

  const handleReset = () => {
    Object.assign(formData, createDefaultData());
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
    selectedClusters.value[ClusterTypes.MONGO_REPLICA_SET] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .db-backup-page {
    padding-bottom: 20px;

    .db-backup-form {
      .bk-form-label {
        font-size: 12px;
      }
    }
  }
</style>
