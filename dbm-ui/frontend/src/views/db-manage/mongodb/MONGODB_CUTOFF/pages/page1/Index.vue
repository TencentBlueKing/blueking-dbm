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
    <div class="mongo-db-replace-page">
      <BkAlert
        closable
        theme="info"
        :title="t('整机替换：将原主机上的所有实例搬迁到同等规格的新主机')" />
      <DbForm
        ref="form"
        class="toolbox-form mt-16"
        form-type="vertical"
        :model="formData">
        <DbFormItem
          :label="t('集群类型')"
          property="cluster_type"
          required>
          <BkRadioGroup
            v-model="formData.cluster_type"
            style="width: 400px"
            type="card">
            <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
              {{ t('副本集集群') }}
            </BkRadioButton>
            <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
              {{ t('分片集群') }}
            </BkRadioButton>
          </BkRadioGroup>
        </DbFormItem>
        <EditableTable
          :key="formData.cluster_type"
          ref="editableTable"
          class="mt16 mb16"
          :model="tableData"
          :rules="rules">
          <EditableTableRow
            v-for="(item, index) in tableData"
            :key="index">
            <EditHostColumn
              v-model="item.host"
              :label="t('待替换的主机')"
              :placeholder="t('请输入IP（单个）')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleBatchEdit" />
            <EditableTableColumn
              field="machine_type"
              :label="t('角色类型')"
              :width="200">
              <EditBlock
                v-model="item.host.machine_type"
                :placeholder="t('输入主机后自动生成')">
                {{ getRoleText(item) }}
              </EditBlock>
            </EditableTableColumn>
            <RelatedClusterColumn
              v-model="item.host"
              :rowspan="item.rowspan" />
            <EditSpecColumn
              v-model="item.spec_id"
              :bk-cloud-id="item.host.bk_cloud_id"
              :cluster-type="item.host.cluster_type"
              :current-spec-ids="item.host.spec_config?.id ? [item.host.spec_config.id] : []"
              field="spec_id"
              :label="t('新机规格')"
              :label-tip="t('默认使用部署方案中选定的规格，将从资源池自动匹配机器')"
              :machine-type="item.host.machine_type" />
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="tableData" />
          </EditableTableRow>
        </EditableTable>
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
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { type Mongodb } from '@services/model/ticket/ticket';
  import { getMongoInstancesList, getMongoTopoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useTicketDetail } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import EditableTable, {
    Block as EditBlock,
    Column as EditableTableColumn,
    Row as EditableTableRow,
  } from '@components/editable-table/Index.vue';
  import { type IValue, type PanelListType } from '@components/instance-selector/Index.vue';

  import TicketRemark from '@views/db-manage/common/TicketRemark.vue';
  import EditSpecColumn from '@views/db-manage/common/toolbox-field/edit-spec/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/operation-column/Index.vue';
  import EditHostColumn from '@views/db-manage/mongodb/common/toolbox-field/edit-host/Index.vue';

  import RelatedClusterColumn from './components/RelatedClusterColumn.vue';

  export interface IDataRow {
    host: {
      id?: number;
      ip?: string;
      master_domain?: string;
      cluster_id?: number;
      cluster_type?: string;
      machine_type?: string;
      shard?: string;
      bk_cloud_id?: number;
      related_clusters?: {
        id: number;
        name: string;
        master_domain: string;
        immute_domain: string;
        cluster_type: string;
      }[];
      spec_config?: {
        id?: number;
      };
    };
    spec_id?: number;
    rowspan: number;
  }

  const createRowData = (values?: Partial<IDataRow>) => ({
    host: values?.host ? values.host : { ip: '' },
    spec_id: values?.spec_id,
    rowspan: values?.rowspan || 1,
  });

  const createDefaultFormData = () => ({
    cluster_type: ClusterTypes.MONGO_REPLICA_SET,
    remark: '',
  });

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  useTicketDetail<Mongodb.Cutoff>(TicketTypes.MONGODB_CUTOFF, {
    onSuccess(ticketDetail) {
      const { details, remark } = ticketDetail;
      const { infos, clusters } = details;
      Object.assign(formData, {
        cluster_type: clusters[infos[0].cluster_id].cluster_type,
        remark,
      });

      nextTick(() => {
        tableData.value = infos.flatMap((infoItem) => {
          const machineInfoList = [...infoItem.mongo_config, ...infoItem.mongodb, ...infoItem.mongos];
          return machineInfoList.map((machineInfo) =>
            createRowData({
              host: {
                ip: machineInfo.ip,
              },
              spec_id: machineInfo.spec_id,
            }),
          );
        });
      });
    },
  });

  const formRef = useTemplateRef('form');
  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'host.ip': [
      {
        validator: (value: string) => {
          if (value) {
            const hostList = tableData.value.filter((row) => row.host.ip === value);
            return hostList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('待替换的主机重复'),
      },
      {
        validator: (value: string) => {
          const row = tableData.value.find((tableItem) => tableItem.host.ip === value);
          if (row) {
            const nodeCountMap = clusterNodeCount.value[row.host.cluster_id!];
            if (row.host.cluster_type === ClusterTypes.MONGO_REPLICA_SET) {
              if (nodeCountMap.mongodb.some((mongodbItem) => mongodbItem > 1)) {
                return t('同一个副本集，一次只能替换一个节点');
              }
              return true;
            }
            if (nodeCountMap.mongo_config.some((mongoConfigItem) => mongoConfigItem > 1)) {
              return t('config一次只能替换一个节点');
            }
            if (nodeCountMap.mongodb.some((mongoConfigItem) => mongoConfigItem > 1)) {
              return t('同一个shard，同时只能替换一个节点');
            }
          }
          return true;
        },
        trigger: 'change',
        message: '',
      },
    ],
  };

  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof EditHostColumn>['selected'] = {
      ['mongoCluster']: [],
    };
    tableData.value.forEach((tableRow) => {
      const { cluster_id: id, master_domain: masterDomain } = tableRow.host;
      if (id && masterDomain) {
        selectedClusters.mongoCluster.push(tableRow.host as unknown as IValue);
      }
    });
    return selectedClusters;
  });

  const clusterNodeCount = computed(() => {
    const nodeCount = tableData.value.reduce<Record<number, Record<string, number>>>((prev, tableItem) => {
      if (tableItem.host.ip && tableItem.host.cluster_id) {
        let countMap: Record<string, number> = {};
        const machineType = tableItem.host.machine_type!;
        const shard = tableItem.host.shard!;
        if (prev[tableItem.host.cluster_id]) {
          countMap = prev[tableItem.host.cluster_id];
          if (
            tableItem.host.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER &&
            tableItem.host.machine_type === 'mongodb'
          ) {
            countMap[shard] = countMap[shard] ? countMap[shard] + 1 : 1;
          } else {
            countMap[machineType] = countMap[machineType] ? countMap[machineType] + 1 : countMap[machineType];
          }
        } else {
          if (
            tableItem.host.cluster_type === ClusterTypes.MONGO_SHARED_CLUSTER &&
            tableItem.host.machine_type === 'mongodb'
          ) {
            countMap[shard] = 1;
          } else {
            countMap[machineType] = 1;
          }
        }

        return Object.assign({}, prev, {
          [tableItem.host.cluster_id]: countMap,
        });
      }
      return prev;
    }, {});

    return Object.entries(nodeCount).reduce<Record<number, Record<string, number[]>>>((prev, [clusterId, countMap]) => {
      const typeCountMap: Record<string, number[]> = {
        mongos: [],
        mongodb: [],
        mongo_config: [],
      };
      Object.entries(countMap).forEach(([type, count]) => {
        if (type in typeCountMap) {
          typeCountMap[type].push(count);
        } else {
          typeCountMap.mongodb.push(count);
        }
      });
      return Object.assign({}, prev, {
        [clusterId]: typeCountMap,
      });
    }, {});
  });

  const tabListConfig = computed(
    () =>
      ({
        mongoCluster: [
          {
            name: t('待替换的主机'),
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getMongoTopoList>) =>
                getMongoTopoList({
                  ...params,
                  cluster_type: formData.cluster_type,
                }),
            },
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getMongoInstancesList>) =>
                getMongoInstancesList({
                  ...params,
                  cluster_type: formData.cluster_type,
                }),
              multiple: true,
            },
          },
          {
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getMongoTopoList>) =>
                getMongoTopoList({
                  ...params,
                  cluster_type: formData.cluster_type,
                }),
            },
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getMongoInstancesList>) =>
                getMongoInstancesList({
                  ...params,
                  cluster_type: formData.cluster_type,
                }),
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  watch(
    () => formData.cluster_type,
    () => {
      tableData.value = [createRowData()];
    },
  );

  watch(
    () => tableData.value.length,
    () => {
      sortTableByCluster();
    },
  );

  const getRoleText = (row: IDataRow) => {
    const { cluster_type: clusterType, machine_type: machineType, shard } = row.host;
    if (clusterType === ClusterTypes.MONGO_SHARED_CLUSTER && machineType === 'mongodb') {
      return shard;
    }
    return machineType || '';
  };

  const handleBatchEdit = (list: IValue[]) => {
    const newList = list.map((item) =>
      createRowData({
        host: {
          id: item.id,
          ip: item.ip,
          master_domain: item.master_domain,
          cluster_id: item.cluster_id,
          cluster_type: item.cluster_type,
          machine_type: item.machine_type,
          shard: item.shard,
          bk_cloud_id: item.bk_cloud_id,
          related_clusters: item.related_clusters,
          spec_config: {
            id: item.spec_config?.id,
          },
        },
        spec_id: item.spec_config?.id,
      }),
    );

    tableData.value = [...(tableData.value[0].host.ip ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  // 表格排序，方便合并集群显示
  const sortTableByCluster = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    const emptyRowList: IDataRow[] = [];
    tableData.value.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const { master_domain: domain } = item.host;
      if (!domain) {
        emptyRowList.push(item);
        return;
      }
      if (!clusterMap[domain]) {
        clusterMap[domain] = [item];
      } else {
        clusterMap[domain].push(item);
      }
    });

    const sortedList: IDataRow[] = [];
    Object.values(clusterMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
      sortedList.push(...list);
    });

    return [...sortedList, ...emptyRowList];
  };

  const generateRequestParam = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    tableData.value.forEach((item) => {
      if (item.host.ip) {
        const domain = item.host.master_domain!;
        if (!clusterMap[domain]) {
          clusterMap[domain] = [item];
        } else {
          clusterMap[domain].push(item);
        }
      }
    });
    const domains = Object.keys(clusterMap);
    const infos = domains.map((domain) => {
      const sameArr = clusterMap[domain];
      const infoItem = {
        cluster_id: sameArr[0].host.cluster_id,
        mongos: [],
        mongodb: [],
        mongo_config: [],
      } as Record<string, any>;
      sameArr.forEach((item) => {
        const specObj = {
          ip: item.host.ip,
          spec_id: item.spec_id,
          bk_cloud_id: item.host.bk_cloud_id,
        };
        infoItem[item.host.machine_type!].push(specObj);
      });
      return infoItem;
    });
    return infos;
  };

  // 提交
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      await formRef.value!.validate();
      const validateResult = await editableTableRef.value!.validate();
      if (validateResult) {
        const infos = generateRequestParam();
        const params = {
          bk_biz_id: currentBizId,
          remark: formData.remark,
          ticket_type: TicketTypes.MONGODB_CUTOFF,
          details: {
            ip_source: 'resource_pool',
            infos,
          },
        };
        await createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: TicketTypes.MONGODB_CUTOFF,
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
    tableData.value = [createRowData()];
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .mongo-db-replace-page {
    padding-bottom: 20px;
  }
</style>
