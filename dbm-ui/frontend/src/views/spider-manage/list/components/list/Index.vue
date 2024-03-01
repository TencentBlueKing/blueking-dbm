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
          action-id="tendbcluster_apply"
          theme="primary"
          @click="handleApply">
          {{ t('实例申请') }}
        </AuthButton>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择集群'),
          }"
          class="inline-block">
          <AuthButton
            action-id="tendbcluster_authorize_rules"
            class="ml-8"
            :disabled="!hasSelected"
            @click="handleShowAuthorize">
            {{ t('批量授权') }}
          </AuthButton>
        </span>
        <span
          v-bk-tooltips="{
            disabled: hasData,
            content: t('请先创建实例'),
          }"
          class="inline-block">
          <AuthButton
            action-id="tendb_excel_authorize_rules"
            class="ml-8"
            :disabled="!hasData"
            @click="handleShowExcelAuthorize">
            {{ t('导入授权') }}
          </AuthButton>
        </span>
        <DropdownExportExcel
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="spider" />
      </div>
      <DbSearchSelect
        v-model="searchValues"
        :data="searchData"
        :placeholder="t('集群名称_访问入口_IP')"
        style="width: 320px; margin-left: auto"
        unique-select
        @change="fetchTableData" />
    </div>
    <div
      class="table-wrapper"
      :class="{
        'is-shrink-table': isStretchLayoutOpen,
      }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getTendbClusterList"
        :pagination-extra="paginationExtra"
        :row-class="setRowClass"
        selectable
        :settings="settings"
        @selection="handleTableSelected"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <DbSideslider
    v-model:is-show="isShowScaleUp"
    :disabled-confirm="!isChangeScaleUpForm"
    :title="t('TenDBCluster扩容接入层name', { name: operationData.cluster_name })"
    width="960">
    <ScaleUp
      v-model:is-change="isChangeScaleUpForm"
      :data="operationData" />
  </DbSideslider>
  <DbSideslider
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
  </DbSideslider>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.TENDBCLUSTER"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selected"
    :tab-list="[ClusterTypes.TENDBCLUSTER]"
    @success="handleClearSelected" />
  <ExcelAuthorize
    v-model:is-show="excelAuthorizeShow"
    :cluster-type="ClusterTypes.TENDBCLUSTER"
    :ticket-type="TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES" />
  <EditEntryConfig
    :id="clusterId"
    v-model:is-show="showEditEntryConfig"
    :get-detail-info="getSpiderDetail" />
</template>

<script setup lang="tsx">
  import { Checkbox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import TendbClusterModel from '@services/model/spider/tendbCluster';
  import {
    getSpiderDetail,
    getSpiderInstanceList,
    getTendbClusterList,
  } from '@services/source/spider';
  import { createTicket } from '@services/source/ticket';
  import type { ResourceItem } from '@services/types';

  import {
    useCopy,
    useInfo,
    useInfoWithIcon,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import ExcelAuthorize from '@components/cluster-common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import EditEntryConfig from '@components/cluster-entry-config/Index.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
    messageWarn,
  } from '@utils';

  import CapacityChange from './components/CapacityChange.vue';
  import ScaleUp from './components/ScaleUp.vue';
  import Shrink from './components/Shrink.vue';

  interface IColumn {
    data: TendbClusterModel
  }

  const route = useRoute();
  const router = useRouter();
  const { t, locale } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();
  const { currentBizId } = useGlobalBizs();
  const copy = useCopy();
  const ticketMessage = useTicketMessage();

  const searchData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名'),
      id: 'name',
    },
    {
      name: t('域名'),
      id: 'domain',
    },
    {
      name: 'IP',
      id: 'ip',
    },
  ];

  const clusterId = defineModel<number>('clusterId');

  const tableRef = ref();
  const isShowScaleUp = ref(false);
  const isShowShrink = ref(false);
  const isShowCapacityChange = ref(false);
  const isChangeScaleUpForm = ref(false);
  const isChangeShrinkForm = ref(false);
  const isChangeCapacityForm = ref(false);
  const removeMNTInstanceIds = ref<number[]>([]);
  const searchValues = ref<Array<any>>([]);
  const excelAuthorizeShow = ref(false);
  const showEditEntryConfig = ref(false);
  const clusterAuthorizeShow = ref(false);

  const selected = shallowRef<ResourceItem[]>([]);
  const operationData = shallowRef({} as TendbClusterModel);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const hasData = computed(() => tableRef.value?.getData().length > 0);
  const isCN = computed(() => locale.value === 'zh-cn');
  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });
  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 200 : 300;
    }
    return 60;
  });
  const searchIp = computed<string[]>(() => {
    const ipObj = searchValues.value.find(item => item.id === 'ip');
    if (ipObj) {
      return [ipObj.values[0].id];
    }
    return [];
  });
  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 80,
    },
    {
      label: t('主访问入口'),
      field: 'master_domain',
      fixed: 'left',
      width: 200,
      minWidth: 200,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="tendbcluster_view"
                resource={data.id}
                permission={data.permission.tendbcluster_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.masterDomainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                {data.master_domain && (
                  <db-icon
                    type="copy"
                    v-bk-tooltips={t('复制主访问入口')}
                    onClick={() => copy(data.masterDomainDisplayName)} />
                )}
                <auth-button
                  v-bk-tooltips={t('修改入口配置')}
                  action-id="access_entry_edit"
                  resource="tendbcluster"
                  permission={data.permission.access_entry_edit}
                  text
                  theme="primary"
                  onClick={() => handleOpenEntryConfig(data)}>
                  <db-icon type="edit" />
                </auth-button>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 200,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => (
        <div class="cluster-name-container">
          <div
            class="cluster-name text-overflow"
            v-overflow-tips>
            <span>
              {data.cluster_name}
            </span>
          </div>
          {data.temporary_info?.source_cluster && <bk-popover theme="light" placement="top" width={280}>
            {{
              default: () => <db-icon type="clone" style="color: #1CAB88;margin-left: 5px;cursor: pointer;"/>,
              content: (
                <div class="struct-cluster-source-popover">
                  <div class="title">{t('构造集群')}</div>
                  <div class="item-row">
                    <div class="label">{t('构造源集群')}：</div>
                    <div class="content">
                      <bk-overflow-title type="tips">{data.temporary_info?.source_cluster}</bk-overflow-title>
                      </div>
                  </div>
                  <div class="item-row">
                    <div class="label">{t('关联单据')}：</div>
                    <div class="content" style="color: #3A84FF;" onClick={() => handleClickRelatedTicket(data.temporary_info.ticket_id)}>{data.temporary_info.ticket_id}</div>
                  </div>
                </div>
              ),
            }}
          </bk-popover>}
          <div class="cluster-tags">
            {
              data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
            }
            {
              data.isOffline && !data.isStarting && (
                <db-icon
                svg
                type="yijinyong"
                class="cluster-tag"
                style="width: 38px; height: 16px;" />
               )
            }
            {
              isRecentDays(data.create_at, 24 * 3)
                ? <span class="glob-new-tag cluster-tag" data-text="NEW" />
                : null
            }
          </div>
          <db-icon
            type="copy"
            v-bk-tooltips={t('复制集群名称')}
            onClick={() => copy(data.cluster_name)} />
        </div>
      ),
    },
    {
      label: t('从访问入口'),
      field: 'slave_domain',
      minWidth: 200,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => (
        <div class="domain">
          <span
            class="text-overflow"
            v-overflow-tips>
            {data.slaveDomainDisplayName || '--'}
          </span>
          {
            data.slave_domain
            && (
              <db-icon
                type="copy"
                v-bk-tooltips={t('复制从访问入口')}
                onClick={() => copy(data.slaveDomainDisplayName)} />
            )
          }
          <auth-button
            v-bk-tooltips={t('修改入口配置')}
            action-id="access_entry_edit"
            resource="tendbcluster"
            permission={data.permission.access_entry_edit}
            text
            theme="primary"
            onClick={() => handleOpenEntryConfig(data)}>
            <db-icon type="edit" />
          </auth-button>
        </div>
      ),
    },
    // {
    //   label: t('MySQL版本'),
    //   field: 'version',
    //   width: 120,
    //   render: ({ data }: IColumn) => data.major_version,
    // },
    {
      label: t('管控区域'),
      width: 120,
      field: 'bk_cloud_name',
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 100,
      render: ({ data }: IColumn) => {
        const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: 'Spider Master',
      field: 'spider_master',
      minWidth: 180,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => {
        if (data.spider_master.length === 0) return '--';
        return (
          <RenderInstances
            highlightIps={searchIp.value}
            data={data.spider_master}
            title={t('【inst】实例预览', {
              inst: data.master_domain, title: 'Spider Master',
            })}
            role="spider_master"
            clusterId={data.id}
            dataSource={getSpiderInstanceList}
          />
        );
      },
    },
    {
      label: 'Spider Slave',
      field: 'spider_slave',
      minWidth: 180,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => {
        if (data.spider_slave.length === 0) return '--';
        return (
          <RenderInstances
            highlightIps={searchIp.value}
            data={data.spider_slave}
            title={t('【inst】实例预览', {
              inst: data.master_domain, title: 'Spider slave',
            })}
            role="spider_slave"
            clusterId={data.id}
            dataSource={getSpiderInstanceList}
          />
        );
      },
    },
    {
      label: t('运维节点'),
      field: 'spider_mnt',
      minWidth: 180,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => {
        if (data.spider_mnt.length === 0) return '--';
        return (
          <RenderInstances
            highlightIps={searchIp.value}
            data={data.spider_mnt}
            title={t('【inst】实例预览', {
              inst: data.master_domain, title: t('运维节点'),
            })}
            role="spider_mnt"
            clusterId={data.id}
            dataSource={getSpiderInstanceList}
          />
        );
      },
    },
    {
      label: 'RemoteDB',
      field: 'remote_db',
      minWidth: 220,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => {
        if (data.remote_db.length === 0) return '--';
        return (
          <RenderInstances
            highlightIps={searchIp.value}
            data={data.remote_db}
            title={t('【inst】实例预览', { inst: data.master_domain, title: 'RemoteDB' })}
            role="remote_master"
            clusterId={data.id}
            dataSource={getSpiderInstanceList}>
            {{
              default: ({ data }: { data:TendbClusterModel['remote_db'][0] }) => {
                if (data.shard_id !== undefined) {
                  return `${data.instance}(%_${data.shard_id})`;
                }
                return data.instance;
              },
            }}
          </RenderInstances>
        );
      },
    },
    {
      label: 'RemoteDR',
      field: 'remote_dr',
      minWidth: 220,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => {
        if (data.remote_dr.length === 0) return '--';
        return (
          <RenderInstances
            highlightIps={searchIp.value}
            data={data.remote_dr}
            title={t('【inst】实例预览', { inst: data.master_domain, title: 'RemoteDR' })}
            role="remote_slave"
            clusterId={data.id}
            dataSource={getSpiderInstanceList}>
            {{
              default: ({ data }: { data:TendbClusterModel['remote_dr'][0] }) => {
                if (data.shard_id !== undefined) {
                  return `${data.instance}(%_${data.shard_id})`;
                }
                return data.instance;
              },
            }}
          </RenderInstances>
        );
      },
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      render: ({ data }: IColumn) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      render: ({ data }: IColumn) => <span>{data.region || '--'}</span>,
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ data }: IColumn) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('创建时间'),
      field: 'create_at',
      width: 160,
      render: ({ data }: IColumn) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      render: ({ data }: IColumn) => <span>{data.cluster_time_zone || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: IColumn) => {
        const getOperations = (theme = 'primary') => {
          const operations = [
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                class="mr-8"
                theme={theme}
                action-id="tendbcluster_node_rebalance"
                disabled={data.operationDisabled}
                onClick={() => handleShowCapacityChange(data)}>
                { t('集群容量变更') }
              </auth-button>
            </OperationBtnStatusTips>,
          ];
          if (!data.isOnline) {
            operations.push(...[
              <OperationBtnStatusTips data={data}>
                <auth-button
                  text
                  theme={theme}
                  action-id="tendbcluster_enable_disable"
                  disabled={data.isStarting}
                  permission={data.permission.tendbcluster_enable_disable}
                  resource={data.id}
                  class="mr-8"
                  onClick={() => handleChangeClusterOnline(TicketTypes.TENDBCLUSTER_ENABLE, data)}>
                  { t('启用') }
                </auth-button>
              </OperationBtnStatusTips>,
              <OperationBtnStatusTips data={data}>
                <auth-button
                  text
                  theme={theme}
                  action-id="tendbcluster_destroy"
                  disabled={data.operationDisabled && !data.isOffline}
                  permission={data.permission.tendbcluster_destroy}
                  resource={data.id}
                  class="mr-8"
                  onClick={() => handleDeleteCluster(data)}>
                  { t('删除') }
              </auth-button>
              </OperationBtnStatusTips>,
            ]);
          }
          return operations;
        };
        const getDropdownOperations = () => {
          const operations = [
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                text
                disabled={data.isOffline}
                class="mr-8"
                action-id="tendbcluster_spider_add_nodes"
                onClick={() => handleShowScaleUp(data)}>
                { t('扩容接入层') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                text
                disabled={data.isOffline}
                class="mr-8"
                action-id="tendbcluster_spider_reduce_nodes"
                onClick={() => handleShowShrink(data)}>
                { t('缩容接入层') }
              </auth-button>
            </OperationBtnStatusTips>,
          ];
          if (data.spider_mnt.length > 0) {
            operations.push((
              <auth-button
                text
                class="mr-8"
                action-id="tendbcluster_spider_mnt_destroy"
                onClick={() => handleRemoveMNT(data)}>
                { t('下架运维节点') }
              </auth-button>
            ));
          }
          if (data.spider_slave.length > 0) {
            operations.push((
              <auth-button
                text
                class="mr-8"
                action-id="tendb_spider_slave_destroy"
                onClick={() => handleDestroySlave(data)}>
                { t('下架只读集群') }
              </auth-button>
            ));
          }
          operations.push((
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                disabled={data.operationDisabled}
                class="mr-8"
                action-id="tendbcluster_enable_disable"
                permission={data.permission.tendbcluster_enable_disable}
                resource={data.id}
                onClick={() => handleChangeClusterOnline(TicketTypes.TENDBCLUSTER_DISABLE, data)}>
                { t('禁用') }
              </auth-button>
            </OperationBtnStatusTips>
          ));

          return data.isOnline ? operations : [];
        };

        const renderDropdownOperations = getDropdownOperations();

        return (
          <>
            { getOperations() }
            {
              renderDropdownOperations.length > 0
                ? (
                  <bk-dropdown
                    class="operations-more"
                    trigger="click"
                    popover-options={{ zIndex: 10 }}
                  >
                    {{
                      default: () => <db-icon type="more" />,
                      content: () => (
                        <bk-dropdown-menu class="operations-menu">
                          {
                            renderDropdownOperations.map(opt => <bk-dropdown-item>{opt}</bk-dropdown-item>)
                          }
                        </bk-dropdown-menu>
                      ),
                    }}
                  </bk-dropdown>
                )
                : null
            }
          </>
        );
      },
    },
  ]);

  const handleOpenEntryConfig = (row: TendbClusterModel) => {
    showEditEntryConfig.value  = true;
    clusterId.value = row.id;
  };

  const handleClickRelatedTicket = (billId: number) => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        id: billId,
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
    return classList.filter(cls => cls).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['master_domain'].includes(item.field as string),
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key && key !== 'id') as string[],
    showLineHeight: false,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBCLUSTER_TABLE_SETTINGS, defaultSettings);

  let isInitData = true;
  const fetchTableData = () => {
    tableRef.value?.fetchData({
      ...getSearchSelectorParams(searchValues.value),
    }, {}, isInitData);
    isInitData = false;

    return Promise.resolve([]);
  };

  // 设置轮询
  useRequest(fetchTableData, {
    pollingInterval: 10000,
  });

  // 查看集群详情
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 集群扩容
  const handleShowScaleUp = (data: TendbClusterModel) => {
    isShowScaleUp.value = true;
    operationData.value = data;
  };

  // 集群缩容
  const handleShowShrink = (data: TendbClusterModel) => {
    isShowShrink.value = true;
    operationData.value = data;
  };

  // 集群容量变更
  const handleShowCapacityChange = (data: TendbClusterModel) => {
    isShowCapacityChange.value = true;
    operationData.value = data;
  };

  // 下架运维节点
  const handleRemoveMNT = (data: TendbClusterModel) => {
    useInfo({
      width: 480,
      title: t('确认下架运维节点'),
      content: () => (
        <>
          <p>{t('下架后将无法再访问_请谨慎操作')}</p>
          <div style="text-align: left; padding: 0 24px;">
            <p class="pt-12" style="font-size: 12px;">{t('请勾选要下架的运维节点')}</p>
            <Checkbox.Group class="mnt-checkbox-group" style="flex-wrap: wrap;" v-model={removeMNTInstanceIds.value}>
              {
                data.spider_mnt.map(item => <Checkbox label={item.bk_instance_id}>{item.instance}</Checkbox>)
              }
            </Checkbox.Group>
          </div>
        </>
      ),
      confirmTxt: t('下架'),
      onConfirm: () => {
        if (removeMNTInstanceIds.value.length === 0) {
          messageWarn(t('请勾选要下架的运维节点'));
          return false;
        }
        return createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'TENDBCLUSTER_SPIDER_MNT_DESTROY',
          details: {
            is_safe: true,
            infos: [
              {
                cluster_id: data.id,
                spider_ip_list: data.spider_mnt
                  .filter(item => removeMNTInstanceIds.value.includes(item.bk_instance_id))
                  .map(item => ({
                    ip: item.ip,
                    bk_cloud_id: item.bk_cloud_id,
                  })),
              },
            ],
          },
        })
          .then((res) => {
            ticketMessage(res.id);
            removeMNTInstanceIds.value = [];
            return true;
          })
          .catch(() => false);
      },
      onCancel: () => {
        removeMNTInstanceIds.value = [];
      },
    });
  };

  // 下架只读集群
  const handleDestroySlave = (data: TendbClusterModel) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认下架只读集群'),
      content: t('下架后将无法访问只读集群'),
      onConfirm: () => createTicket({
        bk_biz_id: currentBizId,
        ticket_type: 'TENDBCLUSTER_SPIDER_SLAVE_DESTROY',
        details: {
          is_safe: true,
          cluster_ids: [data.id],
        },
      })
        .then((res) => {
          ticketMessage(res.id);
          return true;
        })
        .catch(() => false),
    });
  };

  // 集群启停
  const handleChangeClusterOnline = (type: TicketTypesStrings, data: TendbClusterModel) => {
    if (!type) return;

    const isOpen = type === TicketTypes.TENDBCLUSTER_ENABLE;
    const title = isOpen ? t('确定启用该集群') : t('确定禁用该集群');
    useInfoWithIcon({
      type: 'warnning',
      title,
      content: () => (
        <div style="word-break: all;">
          {
            isOpen
              ? <p>{t('集群【name】启用后将恢复访问', { name: data.cluster_name })}</p>
              : <p>{t('集群【name】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { name: data.cluster_name })}</p>
          }
        </div>
      ),
      onConfirm: () => createTicket({
        bk_biz_id: currentBizId,
        ticket_type: type,
        details: {
          cluster_ids: [data.id],
        },
      })
        .then((res) => {
          ticketMessage(res.id);
          return true;
        })
        .catch(() => false),
    });
  };

  // 删除集群
  const handleDeleteCluster = (data: TendbClusterModel) => {
    const { cluster_name: name } = data;
    useInfoWithIcon({
      type: 'warnning',
      title: t('确定删除该集群'),
      confirmTxt: t('删除'),
      confirmTheme: 'danger',
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{t('集群【name】被删除后_将进行以下操作', { name })}</p>
          <p>{t('1_删除xx集群', { name })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name })}</p>
          <p>3. {t('回收主机')}</p>
        </div>
      ),
      onConfirm: () => createTicket({
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.TENDBCLUSTER_DESTROY,
        details: {
          cluster_ids: [data.id],
        },
      })
        .then((res) => {
          ticketMessage(res.id);
          return true;
        })
        .catch(() => false),
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

  const handleTableSelected = (data: ResourceItem, list: ResourceItem[]) => {
    selected.value = list;
  };

  const handleShowAuthorize = () => {
    clusterAuthorizeShow.value = true;
  };

  const handleClearSelected = () => {
    tableRef.value.clearSelected();
    selected.value = [];
  };


  const handleShowExcelAuthorize = () => {
    excelAuthorizeShow.value = true;
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
    }

    .is-shrink-table {
      :deep(.bk-table-body) {
        overflow: hidden auto;
      }
    }

    :deep(.cell) {
      line-height: normal !important;

      .domain {
        display: flex;
        align-items: center;
      }

      .db-icon-copy,
      .db-icon-edit {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }

      .operations-more {
        .db-icon-more {
          display: block;
          font-size: @font-size-normal;
          color: @default-color;
          cursor: pointer;

          &:hover {
            background-color: @bg-disable;
            border-radius: 2px;
          }
        }
      }
    }

    :deep(tr:hover) {
      .db-icon-copy,
      .db-icon-edit {
        display: inline-block !important;
      }
    }

    :deep(.is-offline) {
      a {
        color: @gray-color;
      }

      .cell {
        color: @disable-color;
      }
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
        margin: 2px;
        flex-shrink: 0;
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
