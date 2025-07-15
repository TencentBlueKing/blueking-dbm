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
  <div class="kafka-list-page">
    <div class="header-action">
      <AuthButton
        v-db-console="'kafka.clusterManage.instanceApply'"
        action-id="kafka_apply"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <ClusterBatchOperation
        v-db-console="'kafka.clusterManage.batchOperation'"
        :cluster-type="ClusterTypes.KAFKA"
        :selected="selected"
        @success="fetchTableData" />
      <DropdownExportExcel
        v-db-console="'kafka.clusterManage.export'"
        :ids="selectedIds"
        type="kafka" />
      <ClusterIpCopy
        v-db-console="'kafka.clusterManage.batchCopy'"
        :selected="selected" />
      <TagSearch @search="handleTagSearch" />
      <DbSearchSelect
        :data="serachData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <ClusterTable
      ref="tableRef"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.KAFKA"
      :data-source="dataSource"
      :settings="tableSetting"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings">
      <template #operation>
        <OperationColumn :cluster-type="ClusterTypes.KAFKA">
          <template #default="{ data }">
            <div v-db-console="'kafka.clusterManage.manage'">
              <a
                :href="data.access_url"
                target="_blank">
                {{ t('控制台') }}
              </a>
            </div>
            <div v-db-console="'kafka.clusterManage.getAccess'">
              <AuthButton
                action-id="kafka_access_entry_view"
                :disabled="data.isOffline"
                :permission="data.permission.kafka_access_entry_view"
                :resource="data.id"
                text
                @click="handleShowPassword(data)">
                {{ t('获取访问方式') }}
              </AuthButton>
            </div>
            <div v-db-console="'kafka.clusterManage.scaleUp'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="kafka_scale_up"
                  :permission="data.permission.kafka_scale_up"
                  :resource="data.id"
                  text
                  @click="handleShowExpansion(data)">
                  {{ t('扩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'kafka.clusterManage.scaleDown'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="kafka_shrink"
                  :permission="data.permission.kafka_shrink"
                  :resource="data.id"
                  text
                  @click="handleShowShrink(data)">
                  {{ t('缩容') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'kafka.clusterManage.rebalance'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="kafka_rebalance"
                  :permission="data.permission.kafka_rebalance"
                  :resource="data.id"
                  text
                  @click="handleShowRebalance(data)">
                  {{ t('Topic 均衡') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="data.isOffline"
              v-db-console="'kafka.clusterManage.enable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="kafka_enable_disable"
                  :disabled="data.isStarting"
                  :permission="data.permission.kafka_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleEnableCluster([data])">
                  {{ t('启用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-else
              v-db-console="'kafka.clusterManage.disable'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  action-id="kafka_enable_disable"
                  :disabled="data.isOffline || Boolean(data.operationTicketId)"
                  :permission="data.permission.kafka_enable_disable"
                  :resource="data.id"
                  text
                  @click="handleDisableCluster([data])">
                  {{ t('禁用') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div v-db-console="'kafka.clusterManage.delete'">
              <OperationBtnStatusTips :data="data">
                <AuthButton
                  v-bk-tooltips="{
                    disabled: data.isOffline,
                    content: t('请先禁用集群'),
                  }"
                  action-id="kafka_destroy"
                  :disabled="data.isOnline || Boolean(data.operationTicketId)"
                  :permission="data.permission.kafka_destroy"
                  :resource="data.id"
                  text
                  @click="handleDeleteCluster([data])">
                  {{ t('删除') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <ClusterDomainDnsRelation :data="data" />
          </template>
        </OperationColumn>
      </template>
      <template #masterDomain>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.KAFKA"
          field="master_domain"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          :label="t('访问入口')"
          :selected-list="selected"
          @go-detail="handleToDetails"
          @refresh="fetchTableData" />
      </template>
      <template #role>
        <RoleColumn
          :cluster-type="ClusterTypes.KAFKA"
          field="zookeeper"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Zookeeper"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
        <RoleColumn
          :cluster-type="ClusterTypes.KAFKA"
          field="broker"
          :get-table-instance="getTableInstance"
          :is-filter="isFilter"
          label="Broker"
          :search-ip="batchSearchIpInatanceList"
          :selected-list="selected"
          @go-detail="handleToDetails" />
      </template>
    </ClusterTable>
    <ClusterExpansion
      v-if="operationData"
      v-model:is-show="isShowExpandsion"
      :cluster-data="operationData"
      @change="fetchTableData" />
    <ClusterShrink
      v-if="operationData"
      v-model:is-show="isShowShrink"
      :cluster-data="operationData"
      @change="fetchTableData" />
    <TopicRebalance
      v-if="operationData"
      v-model:is-show="isShowRebalance"
      :data="operationData" />
    <BkDialog
      v-model:is-show="isShowPassword"
      render-directive="if"
      :title="t('获取访问方式')"
      :width="600">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id"
        :db-type="DBTypes.KAFKA" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
    <TableDetailDialog
      v-model="isShowDetail"
      :default-offset-left="300"
      @close="handleDetailClose">
      <ClusterDetail
        v-if="clusterId"
        :cluster-id="clusterId" />
    </TableDetailDialog>
  </div>
</template>
<script setup lang="tsx">
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import KafkaModel from '@services/model/kafka/kafka';
  import { getKafkaList } from '@services/source/kafka';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TagSearch from '@components/tag-search/index.vue';

  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import ClusterTable, {
    MasterDomainColumn,
    OperationColumn,
    RoleColumn,
  } from '@views/db-manage/common/cluster-table/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import useGoClusterDetail from '@views/db-manage/hooks/useGoClusterDetail';
  import ClusterDetail from '@views/db-manage/kafka/common/cluster-detail/Index.vue';
  import ClusterExpansion from '@views/db-manage/kafka/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/kafka/common/shrink/Index.vue';

  import { getMenuListSearch, getSearchSelectorParams } from '@utils';

  import TopicRebalance from './components/TopicRebalance.vue';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.KAFKA,
    {
      onSuccess: () => fetchTableData(),
    },
  );

  const {
    clusterDetailClose: handleDetailClose,
    clusterId,
    goClusterDetail: handleToDetails,
    showDetail: isShowDetail,
  } = useGoClusterDetail('KafkaDetail');

  const {
    batchSearchIpInatanceList,
    clearSearchValue,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    isFilter,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchTableData(),
    searchType: ClusterTypes.KAFKA,
  });

  const dataSource = getKafkaList;

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowRebalance = ref(false);
  const isShowPassword = ref(false);
  const selected = ref<KafkaModel[]>([]);
  const tagSearchValue = ref<Record<string, any>>({});

  const operationData = shallowRef<KafkaModel>();

  const getTableInstance = () => tableRef.value;

  const selectedIds = computed(() => selected.value.map((item) => item.id));

  const serachData = computed(() => [
    {
      async: false,
      id: 'domain',
      multiple: true,
      name: t('访问入口'),
    },
    {
      async: false,
      id: 'instance',
      multiple: true,
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'cluster_ids',
      multiple: true,
      name: 'ID',
    },
    {
      id: 'name',
      name: t('集群名称'),
    },
    {
      children: searchAttrs.value.bk_cloud_id,
      id: 'bk_cloud_id',
      multiple: true,
      name: t('管控区域'),
    },
    {
      id: 'creator',
      name: t('创建人'),
    },
    {
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
        },
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      children: searchAttrs.value.major_version,
      id: 'major_version',
      multiple: true,
      name: t('版本'),
    },
    {
      children: searchAttrs.value.region,
      id: 'region',
      multiple: true,
      name: t('地域'),
    },
    {
      children: searchAttrs.value.time_zone,
      id: 'time_zone',
      multiple: true,
      name: t('时区'),
    },
  ]);

  const { settings: tableSetting, updateTableSettings } = useTableSettings(UserPersonalSettings.KAFKA_TABLE_SETTINGS, {
    checked: [
      'domain',
      'status',
      'cluster_stats',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'zookeeper',
      'broker',
      'tag',
    ],
    disabled: ['master_domain'],
  });

  watch(searchValue, () => {
    tableRef.value!.clearSelected();
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, serachData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return serachData.value.filter((item) => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then((res) =>
        res.results.map((item) => ({
          id: item.username,
          name: item.username,
        })),
      );
    }

    // 不需要远层加载
    return serachData.value.find((set) => set.id === item.id)?.children || [];
  };

  const handleSelection = (data: unknown, list: KafkaModel[]) => {
    selected.value = list;
  };

  const handleTagSearch = (params: Record<string, any>) => {
    tagSearchValue.value = params;
    fetchTableData();
  };

  const fetchTableData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData({
      ...searchParams,
      ...tagSearchValue.value,
      ...sortValue,
    });
  };

  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'KafkaApply',
      query: {
        bizId: window.PROJECT_CONFIG.BIZ_ID,
        from: route.name as string,
      },
    });
  };

  // 扩容
  const handleShowExpansion = (clusterData: KafkaModel) => {
    isShowExpandsion.value = true;
    operationData.value = clusterData;
  };

  // 缩容
  const handleShowShrink = (clusterData: KafkaModel) => {
    isShowShrink.value = true;
    operationData.value = clusterData;
  };

  // topic 均衡
  const handleShowRebalance = (clusterData: KafkaModel) => {
    isShowRebalance.value = true;
    operationData.value = clusterData;
  };

  const handleShowPassword = (clusterData: KafkaModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };
</script>
<style lang="less">
  .kafka-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;
      gap: 8px;

      .tag-search-main {
        margin-left: auto;
      }

      .bk-search-select {
        flex: 1;
        max-width: 500px;
      }
    }
  }
</style>
