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
  <div class="spider-manage-list-page">
    <div class="operations">
      <div class="mb-16">
        <AuthButton
          v-db-console="'tendbCluster.clusterManage.instanceApply'"
          action-id="tendbcluster_apply"
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </AuthButton>
        <ClusterBatchOperation
          v-db-console="'tendbCluster.clusterManage.batchOperation'"
          class="ml-8"
          :cluster-type="ClusterTypes.TENDBCLUSTER"
          :selected="selected"
          @success="handleBatchOperationSuccess" />
        <span
          v-bk-tooltips="{
            disabled: hasData,
            content: t('请先创建实例'),
          }"
          v-db-console="'tendbCluster.clusterManage.importAuthorize'"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasData"
            @click="handleShowExcelAuthorize">
            {{ t('导入授权') }}
          </BkButton>
        </span>
        <DropdownExportExcel
          v-db-console="'tendbCluster.clusterManage.export'"
          :ids="selectedIds"
          type="spider" />
        <ClusterIpCopy
          v-db-console="'tendbCluster.clusterManage.batchCopy'"
          :selected="selected" />
      </div>
      <DbSearchSelect
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div
      class="table-wrapper"
      :class="{
        'is-shrink-table': isStretchLayoutOpen,
      }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="fetchData"
        :pagination-extra="paginationExtra"
        :row-class="setRowClass"
        selectable
        :settings="settings"
        :show-overflow="false"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleTableSelected"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- <DbSideslider
    v-model:is-show="isShowScaleUp"
    :disabled-confirm="!isChangeScaleUpForm"
    :title="t('TenDBCluster扩容接入层name', { name: operationData.cluster_name })"
    width="960">
    <ScaleUp
      v-model:is-change="isChangeScaleUpForm"
      :data="operationData" />
  </DbSideslider> -->
  <!-- <DbSideslider
    v-model:is-show="isShowShrink"
    :disabled-confirm="!isChangeShrinkForm"
    :title="t('TenDBCluster缩容接入层name', { name: operationData.cluster_name })"
    width="960">
    <Shrink
      v-model:is-change="isChangeShrinkForm"
      :data="operationData" />
  </DbSideslider>
  <DbSideslider
    v-model:is-show="isShowCapacityChange"
    :disabled-confirm="!isChangeCapacityForm"
    :title="t('TenDBCluster集群容量变更name', { name: operationData.cluster_name })"
    width="960">
    <CapacityChange
      v-model:is-change="isChangeCapacityForm"
      :data="operationData" />
  </DbSideslider> -->
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.TENDBCLUSTER"
    :cluster-types="[ClusterTypes.TENDBCLUSTER, 'tendbclusterSlave']"
    :selected="selected"
    @success="handleClearSelected" />
  <ExcelAuthorize
    v-model:is-show="excelAuthorizeShow"
    :cluster-type="ClusterTypes.TENDBCLUSTER"
    :ticket-type="TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES" />
  <ClusterExportData
    v-if="currentData"
    v-model:is-show="showDataExportSlider"
    :data="currentData"
    :ticket-type="TicketTypes.TENDBCLUSTER_DUMP_DATA" />
</template>

<script setup lang="tsx">
  import { Checkbox, Message } from 'bkui-vue';
  import InfoBox from 'bkui-vue/lib/info-box';
  // import CapacityChange from './components/CapacityChange.vue';
  // import ScaleUp from './components/ScaleUp.vue';
  // import Shrink from './components/Shrink.vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import {
    getTendbclusterInstanceList,
    getTendbClusterList,
    getTendbclusterPrimary,
  } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useCopy, useLinkQueryColumnSerach, useStretchLayout, useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { AccountTypes, ClusterTypes, DBTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue';
  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';
  import EditEntryConfig, { type ClusterEntryInfo } from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderInstances from '@views/db-manage/common/render-instances/RenderInstances.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { getMenuListSearch, getSearchSelectorParams, isRecentDays, messageWarn } from '@utils';

  interface IColumn {
    data: TendbClusterModel;
  }

  const clusterId = defineModel<number>('clusterId');
  const route = useRoute();
  const router = useRouter();
  const { locale, t } = useI18n();
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();
  const { currentBizId } = useGlobalBizs();
  const copy = useCopy();
  const ticketMessage = useTicketMessage();
  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBCLUSTER,
    {
      onSuccess: () => fetchTableData(),
    },
  );

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchTableData(),
    searchType: ClusterTypes.TENDBCLUSTER,
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  // const isShowScaleUp = ref(false);
  // const isShowShrink = ref(false);
  // const isShowCapacityChange = ref(false);
  // const isChangeScaleUpForm = ref(false);
  // const isChangeShrinkForm = ref(false);
  // const isChangeCapacityForm = ref(false);
  const removeMNTInstanceIds = ref<number[]>([]);
  const excelAuthorizeShow = ref(false);
  const clusterAuthorizeShow = ref(false);
  const showDataExportSlider = ref(false);
  const currentData = ref<IColumn['data']>();
  const selected = ref<TendbClusterModel[]>([]);
  const clusterPrimaryMap = ref<Record<string, boolean>>({});
  // const operationData = shallowRef({} as TendbClusterModel);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));
  const tableDataList = computed(() => tableRef.value?.getData<TendbClusterModel>() || []);
  const hasData = computed(() => tableDataList.value.length > 0);
  const isCN = computed(() => locale.value === 'zh-cn');

  const searchSelectData = computed(() => [
    {
      id: 'domain',
      multiple: true,
      name: t('访问入口'),
    },
    {
      id: 'instance',
      multiple: true,
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'id',
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
  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      align: 'left',
      layout: ['total', 'limit', 'list'],
      small: true,
    };
  });
  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 270 : 300;
    }
    return 60;
  });
  const searchIp = computed<string[]>(() => {
    const ipObj = searchValue.value.find((item) => item.id === 'ip');
    if (ipObj && ipObj.values) {
      return [ipObj.values[0].id];
    }
    return [];
  });

  const entrySort = (data: ClusterEntryInfo[]) => data.sort((a) => (a.role === 'master_entry' ? -1 : 1));

  const columns = computed(() => [
    {
      field: 'id',
      fixed: 'left',
      label: 'ID',
      width: 80,
    },
    {
      field: 'master_domain',
      fixed: 'left',
      label: t('主访问入口'),
      minWidth: 280,
      render: ({ data }: IColumn) => (
        <TextOverflowLayout>
          {{
            append: () => (
              <>
                {data.operationTagTips.map((item) => (
                  <RenderOperationTag
                    class='cluster-tag ml-4'
                    data={item}
                  />
                ))}
                {data.isOffline && !data.isStarting && (
                  <bk-tag
                    class='ml-4'
                    size='small'>
                    {t('已禁用')}
                  </bk-tag>
                )}
                {data.isNew && (
                  <bk-tag
                    class='ml-4'
                    size='small'
                    theme='success'>
                    NEW
                  </bk-tag>
                )}
                {data.master_domain && (
                  <RenderCellCopy
                    copyItems={[
                      {
                        label: t('域名'),
                        value: data.master_domain,
                      },
                      {
                        label: t('域名:端口'),
                        value: data.masterDomainDisplayName,
                      },
                    ]}
                  />
                )}
                <span v-db-console='tendbCluster.clusterManage.modifyEntryConfiguration'>
                  <EditEntryConfig
                    id={data.id}
                    bizId={data.bk_biz_id}
                    permission={data.permission.access_entry_edit}
                    resource={DBTypes.TENDBCLUSTER}
                    sort={entrySort}
                    onSuccess={fetchData}>
                    {{
                      prepend: ({ data: cluster }: { data: ClusterEntryInfo }) =>
                        cluster.role === 'master_entry' ? (
                          <bk-tag
                            size='small'
                            theme='success'>
                            {t('主')}
                          </bk-tag>
                        ) : (
                          <bk-tag
                            size='small'
                            theme='info'>
                            {t('从')}
                          </bk-tag>
                        ),
                    }}
                  </EditEntryConfig>
                </span>
              </>
            ),
            default: () => (
              <auth-button
                action-id='tendbcluster_view'
                permission={data.permission.tendbcluster_view}
                resource={data.id}
                theme='primary'
                text
                onClick={() => handleToDetails(data.id)}>
                {data.masterDomainDisplayName}
              </auth-button>
            ),
          }}
        </TextOverflowLayout>
      ),
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'master_domain',
              label: t('域名'),
            },
            {
              field: 'masterDomainDisplayName',
              label: t('域名:端口'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={handleCopyAll}
          onHandleCopySelected={handleCopySelected}>
          {t('主访问入口')}
        </RenderHeadCopy>
      ),
    },
    {
      field: 'cluster_name',
      label: t('集群名称'),
      minWidth: 200,
      render: ({ data }: IColumn) => (
        <TextOverflowLayout>
          {{
            append: () => (
              <>
                {data.temporary_info?.source_cluster && (
                  <bk-popover
                    placement='top'
                    theme='light'>
                    {{
                      content: (
                        <div class='struct-cluster-source-popover'>
                          <div class='title'>{t('构造集群')}</div>
                          <div class='item-row'>
                            <div class='label'>{t('构造源集群')}：</div>
                            <div class='content'>{data.temporary_info?.source_cluster}</div>
                          </div>
                          <div class='item-row'>
                            <div class='label'>{t('关联单据')}：</div>
                            <div
                              class='content'
                              style='color: #3A84FF;'
                              onClick={() => handleClickRelatedTicket(data.temporary_info.ticket_id)}>
                              {data.temporary_info.ticket_id}
                            </div>
                          </div>
                        </div>
                      ),
                      default: () => (
                        <db-icon
                          style='color: #1CAB88;margin-left: 5px;cursor: pointer;'
                          type='clone'
                        />
                      ),
                    }}
                  </bk-popover>
                )}
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  type='copy'
                  onClick={() => copy(data.cluster_name)}
                />
              </>
            ),
            default: () => data.cluster_name,
          }}
        </TextOverflowLayout>
      ),
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'cluster_name',
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={handleCopyAll}
          onHandleCopySelected={handleCopySelected}>
          {t('集群名称')}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
    },
    {
      field: 'slave_domain',
      label: t('从访问入口'),
      minWidth: 200,
      render: ({ data }: IColumn) => (
        <div class='domain'>
          <span
            v-overflow-tips
            class='text-overflow'>
            {data.slaveDomainDisplayName || '--'}
          </span>
          {data.slave_domain && (
            <db-icon
              v-bk-tooltips={t('复制从访问入口')}
              type='copy'
              onClick={() => copy(data.slaveDomainDisplayName)}
            />
          )}
          <span v-db-console='tendbCluster.clusterManage.modifyEntryConfiguration'>
            <EditEntryConfig
              id={data.id}
              bizId={data.bk_biz_id}
              permission={data.permission.access_entry_edit}
              resource={DBTypes.TENDBCLUSTER}
              sort={entrySort}
              onSuccess={fetchData}>
              {{
                prepend: ({ data: cluster }: { data: ClusterEntryInfo }) =>
                  cluster.role === 'master_entry' ? (
                    <bk-tag
                      size='small'
                      theme='success'>
                      {t('主')}
                    </bk-tag>
                  ) : (
                    <bk-tag
                      size='small'
                      theme='info'>
                      {t('从')}
                    </bk-tag>
                  ),
              }}
            </EditEntryConfig>
          </span>
        </div>
      ),
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'slave_domain',
              label: t('域名'),
            },
            {
              field: 'slaveDomainDisplayName',
              label: t('域名:端口'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={handleCopyAll}
          onHandleCopySelected={handleCopySelected}>
          {t('从访问入口')}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
    },
    // {
    //   label: t('MySQL版本'),
    //   field: 'version',
    //   width: 120,
    //   render: ({ data }: IColumn) => data.major_version,
    // },
    {
      field: 'status',
      filter: {
        checked: columnCheckedMap.value.status,
        list: [
          {
            text: t('正常'),
            value: 'normal',
          },
          {
            text: t('异常'),
            value: 'abnormal',
          },
        ],
      },
      label: t('状态'),
      render: ({ data }: IColumn) => {
        const info =
          data.status === 'normal' ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      width: 100,
    },
    {
      field: 'cluster_stats',
      label: t('容量使用率'),
      render: ({ data }: IColumn) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />,
      showOverflowTooltip: false,
      width: 240,
    },
    {
      field: 'spider_master',
      label: 'Spider Master',
      minWidth: 200,
      render: ({ data }: IColumn) => (
        <RenderInstances
          title={t('【inst】实例预览', {
            inst: data.master_domain,
            title: 'Spider Master',
          })}
          clusterId={data.id}
          data={data.spider_master}
          dataSource={getTendbclusterInstanceList}
          highlightIps={searchIp.value}
          role='spider_master'>
          {{
            append: ({ data }: { data: TendbClusterModel['spider_master'][number] }) =>
              clusterPrimaryMap.value[data.ip] && (
                <bk-tag
                  class='is-primary'
                  size='small'>
                  Primary
                </bk-tag>
              ),
          }}
        </RenderInstances>
      ),
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'ip',
              label: 'IP',
            },
            {
              field: 'instance',
              label: t('实例'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={(field) => handleCopyAll(field, 'spider_master')}
          onHandleCopySelected={(field) => handleCopySelected(field, 'spider_master')}>
          {'Spider Master'}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
      width: 200,
    },
    {
      field: 'spider_slave',
      label: 'Spider Slave',
      minWidth: 200,
      render: ({ data }: IColumn) => {
        if (data.spider_slave.length === 0) return '--';
        return (
          <RenderInstances
            title={t('【inst】实例预览', {
              inst: data.master_domain,
              title: 'Spider slave',
            })}
            clusterId={data.id}
            data={data.spider_slave}
            dataSource={getTendbclusterInstanceList}
            highlightIps={searchIp.value}
            role='spider_slave'
          />
        );
      },
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'ip',
              label: 'IP',
            },
            {
              field: 'instance',
              label: t('实例'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={(field) => handleCopyAll(field, 'spider_slave')}
          onHandleCopySelected={(field) => handleCopySelected(field, 'spider_slave')}>
          {'Spider Slave'}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
      width: 200,
    },
    {
      field: 'spider_mnt',
      label: t('运维节点'),
      minWidth: 200,
      render: ({ data }: IColumn) => {
        if (data.spider_mnt.length === 0) return '--';
        return (
          <RenderInstances
            title={t('【inst】实例预览', {
              inst: data.master_domain,
              title: t('运维节点'),
            })}
            clusterId={data.id}
            data={data.spider_mnt}
            dataSource={getTendbclusterInstanceList}
            highlightIps={searchIp.value}
            role='spider_mnt'
          />
        );
      },
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'ip',
              label: 'IP',
            },
            {
              field: 'instance',
              label: t('实例'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={(field) => handleCopyAll(field, 'spider_mnt')}
          onHandleCopySelected={(field) => handleCopySelected(field, 'spider_mnt')}>
          {t('运维节点')}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
      width: 200,
    },
    {
      field: 'remote_db',
      label: 'RemoteDB',
      minWidth: 250,
      render: ({ data }: IColumn) => {
        if (data.remote_db.length === 0) return '--';
        return (
          <RenderInstances
            clusterId={data.id}
            data={data.remote_db}
            dataSource={getTendbclusterInstanceList}
            highlightIps={searchIp.value}
            role='remote_master'
            title={t('【inst】实例预览', { inst: data.master_domain, title: 'RemoteDB' })}>
            {{
              default: ({ data }: { data: TendbClusterModel['remote_db'][0] }) => {
                if (data.shard_id !== undefined) {
                  return `${data.instance}(%_${data.shard_id})`;
                }
                return data.instance;
              },
            }}
          </RenderInstances>
        );
      },
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'ip',
              label: 'IP',
            },
            {
              field: 'instance',
              label: t('实例'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={(field) => handleCopyAll(field, 'remote_db')}
          onHandleCopySelected={(field) => handleCopySelected(field, 'remote_db')}>
          {'RemoteDB'}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
      width: 250,
    },
    {
      field: 'remote_dr',
      label: 'RemoteDR',
      minWidth: 250,
      render: ({ data }: IColumn) => {
        if (data.remote_dr.length === 0) return '--';
        return (
          <RenderInstances
            clusterId={data.id}
            data={data.remote_dr}
            dataSource={getTendbclusterInstanceList}
            highlightIps={searchIp.value}
            role='remote_slave'
            title={t('【inst】实例预览', { inst: data.master_domain, title: 'RemoteDR' })}>
            {{
              default: ({ data }: { data: TendbClusterModel['remote_dr'][0] }) => {
                if (data.shard_id !== undefined) {
                  return `${data.instance}(%_${data.shard_id})`;
                }
                return data.instance;
              },
            }}
          </RenderInstances>
        );
      },
      renderHead: () => (
        <RenderHeadCopy
          config={[
            {
              field: 'ip',
              label: 'IP',
            },
            {
              field: 'instance',
              label: t('实例'),
            },
          ]}
          hasSelected={hasSelected.value}
          onHandleCopyAll={(field) => handleCopyAll(field, 'remote_dr')}
          onHandleCopySelected={(field) => handleCopySelected(field, 'remote_dr')}>
          {'RemoteDR'}
        </RenderHeadCopy>
      ),
      showOverflowTooltip: false,
      width: 250,
    },
    {
      field: 'major_version',
      filter: {
        checked: columnCheckedMap.value.major_version,
        list: columnAttrs.value.major_version,
      },
      label: t('版本'),
      minWidth: 100,
      render: ({ data }: IColumn) => <span>{data.major_version || '--'}</span>,
    },
    {
      field: 'disaster_tolerance_level',
      label: t('容灾要求'),
      minWidth: 100,
      render: ({ data }: IColumn) => data.disasterToleranceLevelName || '--',
    },

    {
      field: 'region',
      filter: {
        checked: columnCheckedMap.value.region,
        list: columnAttrs.value.region,
      },
      label: t('地域'),
      minWidth: 100,
      render: ({ data }: IColumn) => <span>{data.region || '--'}</span>,
    },
    {
      field: 'spec_name',
      label: t('规格'),
      minWidth: 180,
      render: ({ data }: IColumn) => data.cluster_spec.spec_name || '--',
    },
    {
      field: 'bk_cloud_id',
      filter: {
        checked: columnCheckedMap.value.bk_cloud_id,
        list: columnAttrs.value.bk_cloud_id,
      },
      label: t('管控区域'),
      render: ({ data }: IColumn) => (data.bk_cloud_name ? `${data.bk_cloud_name}[${data.bk_cloud_id}]` : '--'),
      width: 120,
    },
    {
      field: 'creator',
      label: t('创建人'),
      render: ({ data }: IColumn) => <span>{data.creator || '--'}</span>,
      width: 140,
    },
    {
      field: 'create_at',
      label: t('部署时间'),
      render: ({ data }: IColumn) => <span>{data.createAtDisplay || '--'}</span>,
      sort: true,
      width: 250,
    },
    {
      field: 'cluster_time_zone',
      filter: {
        checked: columnCheckedMap.value.time_zone,
        list: columnAttrs.value.time_zone,
      },
      label: t('时区'),
      render: ({ data }: IColumn) => <span>{data.cluster_time_zone || '--'}</span>,
      width: 100,
    },
    {
      field: '',
      fixed: isStretchLayoutOpen.value ? false : 'right',
      label: t('操作'),
      render: ({ data }: IColumn) => {
        const getOperations = () => {
          const operations = [
            <bk-button
              v-db-console='mysql.haClusterList.authorize'
              class='mr-8'
              disabled={data.isOffline}
              theme='primary'
              text
              onClick={() => handleShowAuthorize([data])}>
              {t('授权')}
            </bk-button>,
            <auth-button
              v-db-console='tendbCluster.clusterManage.webconsole'
              action-id='tendbcluster_webconsole'
              class='mr-8'
              disabled={data.isOffline}
              permission={data.permission.tendbcluster_webconsole}
              resource={data.id}
              theme='primary'
              text
              onClick={() => handleGoWebconsole(data.id)}>
              Webconsole
            </auth-button>,
            <auth-button
              v-db-console='tendbCluster.clusterManage.exportData'
              action-id='tendbcluster_dump_data'
              class='mr-16'
              disabled={data.isOffline}
              permission={data.permission.tendbcluster_dump_data}
              resource={data.id}
              theme='primary'
              text
              onClick={() => handleShowDataExportSlider(data)}>
              {t('导出数据')}
            </auth-button>,
          ];
          return operations;
        };
        const getDropdownOperations = () => {
          const operations = [
            <bk-dropdown-item
              v-bk-tooltips={{
                content: t('无运维节点'),
                disabled: data.spider_mnt.length > 0,
              }}
              v-db-console='tendbCluster.clusterManage.removeMNTNode'>
              <auth-button
                action-id='tendbcluster_spider_mnt_destroy'
                class='mr-8'
                disabled={data.spider_mnt.length === 0 || data.isOffline}
                permission={data.permission.tendbcluster_spider_mnt_destroy}
                resource={data.id}
                text
                onClick={() => handleRemoveMNT(data)}>
                {t('下架运维节点')}
              </auth-button>
            </bk-dropdown-item>,
            <bk-dropdown-item
              v-bk-tooltips={{
                content: t('无只读集群'),
                disabled: data.spider_slave.length > 0,
              }}
              v-db-console='tendbCluster.clusterManage.removeReadonlyNode'>
              <auth-button
                action-id='tendb_spider_slave_destroy'
                class='mr-8'
                disabled={data.spider_slave.length === 0 || data.isOffline}
                permission={data.permission.tendb_spider_slave_destroy}
                resource={data.id}
                text
                onClick={() => handleDestroySlave(data)}>
                {t('下架只读集群')}
              </auth-button>
            </bk-dropdown-item>,
          ];

          if (data.isOnline) {
            operations.push(
              <bk-dropdown-item v-db-console='tendbCluster.clusterManage.disable'>
                <OperationBtnStatusTips data={data}>
                  <auth-button
                    action-id='tendbcluster_enable_disable'
                    class='mr-8'
                    disabled={data.operationDisabled}
                    permission={data.permission.tendbcluster_enable_disable}
                    resource={data.id}
                    text
                    onClick={() => handleDisableCluster([data])}>
                    {t('禁用')}
                  </auth-button>
                </OperationBtnStatusTips>
              </bk-dropdown-item>,
            );
          }
          if (data.isOffline) {
            operations.push(
              ...[
                <bk-dropdown-item v-db-console='tendbCluster.clusterManage.enable'>
                  <OperationBtnStatusTips data={data}>
                    <auth-button
                      v-db-console='tendbCluster.clusterManage.enable'
                      action-id='tendbcluster_enable_disable'
                      class='mr-8'
                      disabled={data.isStarting}
                      permission={data.permission.tendbcluster_enable_disable}
                      resource={data.id}
                      text
                      onClick={() => handleEnableCluster([data])}>
                      {t('启用')}
                    </auth-button>
                  </OperationBtnStatusTips>
                </bk-dropdown-item>,
              ],
            );
          }

          operations.push(
            <bk-dropdown-item v-db-console='tendbCluster.clusterManage.delete'>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  v-bk-tooltips={{
                    content: t('请先禁用集群'),
                    disabled: data.isOffline,
                  }}
                  v-db-console='tendbCluster.clusterManage.delete'
                  action-id='tendbcluster_destroy'
                  class='mr-8'
                  disabled={data.isOnline || Boolean(data.operationTicketId)}
                  permission={data.permission.tendbcluster_destroy}
                  resource={data.id}
                  text
                  onClick={() => handleDeleteCluster([data])}>
                  {t('删除')}
                </auth-button>
              </OperationBtnStatusTips>
            </bk-dropdown-item>,
          );

          return operations;
        };

        const renderDropdownOperations = getDropdownOperations();
        return (
          <>
            {getOperations()}
            {renderDropdownOperations.length > 0 ? (
              <MoreActionExtend v-db-console='tendbCluster.clusterManage.moreOperation'>
                {{
                  default: () => renderDropdownOperations,
                }}
              </MoreActionExtend>
            ) : null}
          </>
        );
      },
      width: tableOperationWidth.value,
    },
  ]);

  const { run: getSpiderClusterPrimaryRun } = useRequest(getTendbclusterPrimary, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        clusterPrimaryMap.value = data.reduce<Record<string, boolean>>((acc, cur) => {
          const ip = cur.primary.split(':')[0];
          if (ip) {
            // eslint-disable-next-line no-param-reassign
            acc[ip] = true;
          }
          return acc;
        }, {});
      }
    },
  });

  const { runAsync: fetchData } = useRequest(getTendbClusterList, {
    manual: true,
    onSuccess(data) {
      const clusterIds = data.results.map((item) => item.id);
      if (clusterIds.length > 0) {
        getSpiderClusterPrimaryRun({
          cluster_ids: clusterIds,
        });
      }
    },
  });

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchSelectData.value.filter((item) => !selected.includes(item.id));
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
    return searchSelectData.value.find((set) => set.id === item.id)?.children || [];
  };

  const handleClickRelatedTicket = (billId: number) => {
    const route = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: billId,
      },
    });
    window.open(route.href);
  };

  // 设置行样式
  const setRowClass = (row: TendbClusterModel) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter((cls) => cls).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: [
      'master_domain',
      'slave_domain',
      'status',
      'cluster_stats',
      'spider_master',
      'spider_slave',
      'spider_mnt',
      'remote_db',
      'remote_dr',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'spec_name',
      'bk_cloud_id',
    ],
    fields: (columns.value || [])
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['master_domain'].includes(item.field as string),
        field: item.field as string,
        label: item.label as string,
      })),
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.TENDBCLUSTER_TABLE_SETTINGS,
    defaultSettings,
  );

  let isInitData = true;
  const fetchTableData = () => {
    tableRef.value?.fetchData(
      {
        ...getSearchSelectorParams(searchValue.value),
      },
      { ...sortValue },
      isInitData,
    );
    isInitData = false;

    return Promise.resolve([]);
  };

  const handleCopy = <T,>(dataList: T[], field: keyof T) => {
    const copyList = dataList.reduce((prevList, tableItem) => {
      const value = String(tableItem[field]);
      if (value && value !== '--' && !prevList.includes(value)) {
        prevList.push(value);
      }
      return prevList;
    }, [] as string[]);
    copy(copyList.join('\n'));
  };

  // 获取列表数据下的实例子列表
  const getInstanceListByRole = (dataList: TendbClusterModel[], field: keyof TendbClusterModel) =>
    dataList.reduce(
      (result, curRow) => {
        result.push(...(curRow[field] as TendbClusterModel['spider_master']));
        return result;
      },
      [] as TendbClusterModel['spider_master'],
    );

  const handleCopySelected = <T,>(field: keyof T, role?: keyof TendbClusterModel) => {
    if (role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field);
      return;
    }
    handleCopy(selected.value as T[], field);
  };

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof TendbClusterModel) => {
    const allData = await tableRef.value!.getAllData<TendbClusterModel>();
    if (allData.length === 0) {
      Message({
        message: t('暂无数据可复制'),
        theme: 'primary',
      });
      return;
    }
    if (role) {
      handleCopy(getInstanceListByRole(allData, role) as T[], field);
      return;
    }
    handleCopy(allData as T[], field);
  };

  // 查看集群详情
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // // 集群扩容
  // const handleShowScaleUp = (data: TendbClusterModel) => {
  //   isShowScaleUp.value = true;
  //   operationData.value = data;
  // };

  // // 集群缩容
  // const handleShowShrink = (data: TendbClusterModel) => {
  //   isShowShrink.value = true;
  //   operationData.value = data;
  // };

  // // 集群容量变更
  // const handleShowCapacityChange = (data: TendbClusterModel) => {
  //   isShowCapacityChange.value = true;
  //   operationData.value = data;
  // };

  const handleGoWebconsole = (clusterId: number) => {
    router.push({
      name: 'SpiderWebconsole',
      query: {
        clusterId,
      },
    });
  };

  // 下架运维节点
  const handleRemoveMNT = (data: TendbClusterModel) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('下架'),
      content: () => (
        <>
          <p>{t('下架后将无法再访问_请谨慎操作')}</p>
          <div style='text-align: left; padding: 0 24px;'>
            <p
              class='pt-12'
              style='font-size: 12px;'>
              {t('请勾选要下架的运维节点')}
            </p>
            <Checkbox.Group
              v-model={removeMNTInstanceIds.value}
              class='mnt-checkbox-group'
              style='flex-wrap: wrap;'>
              {data.spider_mnt.map((item) => (
                <Checkbox label={item.bk_instance_id}>{item.instance}</Checkbox>
              ))}
            </Checkbox.Group>
          </div>
        </>
      ),
      onCancel: () => {
        removeMNTInstanceIds.value = [];
      },
      onConfirm: () => {
        if (removeMNTInstanceIds.value.length === 0) {
          messageWarn(t('请勾选要下架的运维节点'));
          return false;
        }
        return createTicket({
          bk_biz_id: currentBizId,
          details: {
            infos: [
              {
                cluster_id: data.id,
                old_nodes: {
                  spider_ip_list: data.spider_mnt
                    .filter((item) => removeMNTInstanceIds.value.includes(item.bk_instance_id))
                    .map((item) => ({
                      bk_cloud_id: item.bk_cloud_id,
                      bk_host_id: item.bk_host_id,
                      ip: item.ip,
                    })),
                },
              },
            ],
            is_safe: true,
          },
          ticket_type: 'TENDBCLUSTER_SPIDER_MNT_DESTROY',
        })
          .then((res) => {
            ticketMessage(res.id);
            removeMNTInstanceIds.value = [];
            return true;
          })
          .catch(() => false);
      },
      title: t('确认下架运维节点'),
      width: 480,
    });
  };

  // 下架只读集群
  const handleDestroySlave = (data: TendbClusterModel) => {
    InfoBox({
      content: t('下架后将无法访问只读集群'),
      onConfirm: () =>
        createTicket({
          bk_biz_id: currentBizId,
          details: {
            cluster_ids: [data.id],
            is_safe: true,
          },
          ticket_type: 'TENDBCLUSTER_SPIDER_SLAVE_DESTROY',
        }).then((res) => {
          ticketMessage(res.id);
        }),
      title: t('确认下架只读集群'),
      type: 'warning',
    });
  };

  // 申请实例
  const handleApply = () => {
    router.push({
      name: 'spiderApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleTableSelected = (data: TendbClusterModel, list: TendbClusterModel[]) => {
    selected.value = list;
  };

  const handleShowAuthorize = (list: TendbClusterModel[] = []) => {
    clusterAuthorizeShow.value = true;
    selected.value = list;
  };

  const handleClearSelected = () => {
    tableRef.value!.clearSelected();
    selected.value = [];
  };

  const handleShowDataExportSlider = (data: IColumn['data']) => {
    currentData.value = data;
    showDataExportSlider.value = true;
  };

  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchTableData();
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less" scoped>
  .spider-manage-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .operations {
      display: flex;
      margin-bottom: 16px;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;
    }

    :deep(td .vxe-cell) {
      .domain {
        display: flex;
        flex-wrap: wrap;

        .bk-search-select {
          flex: 1;
          max-width: 320px;
          min-width: 320px;
          margin-left: auto;
        }
      }

      .is-primary {
        color: #531dab !important;
        background: #f9f0ff !important;
      }

      .db-icon-copy,
      .db-icon-visible1 {
        display: none;
        margin-top: 2px;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }

      :deep(.cluster-name-container) {
        display: flex;
        align-items: center;
        padding: 8px 0;
        overflow: hidden;

        .cluster-name {
          line-height: 16px;

          &__alias {
            color: @light-gray;
          }
        }

        .cluster-tags {
          display: flex;
          margin-left: 4px;
          align-items: center;
          flex-wrap: wrap;
        }

        .cluster-tag {
          margin: 2px 0;
          flex-shrink: 0;
        }
      }
    }

    :deep(th:hover),
    :deep(td:hover) {
      .db-icon-copy,
      .db-icon-visible1 {
        display: inline-block !important;
      }
    }

    :deep(.is-offline) {
      a {
        color: @gray-color;
      }

      .vxe-cell {
        color: @disable-color;
      }
    }

    :deep(.operations-more) {
      .db-icon-more {
        font-size: 16px;
        color: @default-color;
        cursor: pointer;

        &:hover {
          background-color: @bg-disable;
          border-radius: 2px;
        }
      }
    }
  }
</style>

<style lang="less">
  .operations-menu {
    .bk-button {
      width: 100%;
      justify-content: flex-start;
    }
  }

  .mnt-checkbox-group {
    flex-wrap: wrap;

    .bk-checkbox {
      margin-top: 8px;
      margin-left: 0;
      flex: 0 0 50%;
    }
  }

  .struct-cluster-source-popover {
    display: flex;
    width: 100%;
    flex-direction: column;
    gap: 12px;
    padding: 2px 0;

    .title {
      font-size: 12px;
      font-weight: 700;
      color: #313238;
    }

    .item-row {
      display: flex;
      width: 100%;
      align-items: center;
      overflow: hidden;

      .label {
        width: 72px;
        text-align: right;
      }

      .content {
        flex: 1;
        overflow: hidden;
        cursor: pointer;
      }
    }
  }
</style>
