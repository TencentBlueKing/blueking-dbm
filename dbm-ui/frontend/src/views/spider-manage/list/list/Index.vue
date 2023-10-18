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
    <div
      class="operations"
      :class="{'is-flex': isFlexHeader}">
      <DbSearchSelect
        v-model="searchValues"
        class="mb-16"
        :data="searchData"
        :placeholder="$t('集群名称_访问入口_IP')"
        style="width: 320px;"
        unique-select
        @change="fetchTableData" />
      <div class="mb-16">
        <BkButton
          theme="primary"
          @click="handleApply">
          {{ $t('实例申请') }}
        </BkButton>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: $t('请选择集群')
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasSelected"
            @click="handleShowAuthorize">
            {{ $t('批量授权') }}
          </BkButton>
        </span>
        <span
          v-bk-tooltips="{
            disabled: hasData,
            content: $t('请先创建实例')
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasData"
            @click="handleShowExcelAuthorize">
            {{ $t('导入授权') }}
          </BkButton>
        </span>
      </div>
    </div>
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': !isFullWidth}"
      :style="{ height: tableHeight }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getSpiderList"
        :pagination-extra="paginationExtra"
        :row-class="setRowClass"
        :settings="settings"
        @selection-change="handleTableSelected"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <DbSideslider
    v-model:is-show="isShowScaleUp"
    :disabled-confirm="!isChangeScaleUpForm"
    :title="$t('TenDBCluster扩容接入层name', { name: operationData.cluster_name })"
    width="960">
    <ScaleUp
      v-model:is-change="isChangeScaleUpForm"
      :data="operationData" />
  </DbSideslider>
  <DbSideslider
    v-model:is-show="isShowShrink"
    :disabled-confirm="!isChangeShrinkForm"
    :title="$t('TenDBCluster缩容接入层name', { name: operationData.cluster_name })"
    width="960">
    <Shrink
      v-model:is-change="isChangeShrinkForm"
      :data="operationData" />
  </DbSideslider>
  <DbSideslider
    v-model:is-show="isShowCapacityChange"
    :disabled-confirm="!isChangeCapacityForm"
    :title="$t('TenDBCluster集群容量变更name', { name: operationData.cluster_name })"
    width="960">
    <CapacityChange
      v-model:is-change="isChangeCapacityForm"
      :data="operationData" />
  </DbSideslider>
  <ClusterAuthorize
    v-model="clusterAuthorizeShow"
    :account-type="AccountTypes.TENDBCLUSTER"
    :cluster-type="ClusterTypes.TENDBCLUSTER"
    :selected="selected"
    :tab-list="[ClusterTypes.TENDBCLUSTER]"
    @success="handleClearSelected" />
  <ExcelAuthorize
    v-model:is-show="excelAuthorizeShow"
    :cluster-type="ClusterTypes.TENDBCLUSTER"
    :ticket-type="TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES" />
</template>

<script setup lang="tsx">
  import { Checkbox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type TendbClusterModel from '@services/model/spider/tendbCluster';
  import {
    getSpiderInstances,
    getSpiderList,
  } from '@services/spider';
  import { createTicket } from '@services/ticket';
  import type { ResourceItem } from '@services/types/clusters';

  import {
    useCopy,
    useInfo,
    useInfoWithIcon,
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
  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import DbStatus from '@components/db-status/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';

  import ExcelAuthorize from '@views/mysql/cluster-management/list/components/MySQLExcelAuthorize.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
    messageWarn,
  } from '@utils';

  import CapacityChange from './components/CapacityChange.vue';
  import ScaleUp from './components/ScaleUp.vue';
  import Shrink from './components/Shrink.vue';

  import type { TableSelectionData } from '@/types/bkui-vue';

  interface IColumn {
    data: TendbClusterModel
  }

  interface Props {
    width: number,
    isFullWidth: boolean,
    dragTrigger: (isLeft: boolean) => void
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const route = useRoute();
  const { t, locale } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const copy = useCopy();
  const ticketMessage = useTicketMessage();

  const searchData = [{
    name: t('集群名'),
    id: 'name',
  }, {
    name: t('域名'),
    id: 'domain',
  }, {
    name: 'IP',
    id: 'ip',
  }];
  const tableRef = ref();
  const isShowScaleUp = ref(false);
  const isShowShrink = ref(false);
  const isShowCapacityChange = ref(false);
  const isChangeScaleUpForm = ref(false);
  const isChangeShrinkForm = ref(false);
  const isChangeCapacityForm = ref(false);
  const removeMNTInstanceIds = ref<number[]>([]);
  const searchValues = ref([]);
  const operationData = shallowRef({} as TendbClusterModel);
  const excelAuthorizeShow = ref(false);
  // excel 授权
  const hasData = computed(() => tableRef.value?.getData().length > 0);
  const isCN = computed(() => locale.value === 'zh-cn');
  const isFlexHeader = computed(() => props.width >= 460);
  const paginationExtra = computed(() => {
    if (props.isFullWidth) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });
  const tableHeight = computed(() => `calc(100% - ${isFlexHeader.value ? 48 : 96}px)`);
  const tableOperationWidth = computed(() => {
    if (props.isFullWidth) {
      return isCN.value ? 200 : 300;
    }
    return 60;
  });
  const columns = computed(() => [
    {
      type: 'selection',
      width: 48,
      minWidth: 48,
      label: '',
      fixed: 'left',
    },
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 80,
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
            <a href="javascript:" onClick={() => handleToDetails(data)}>{data.cluster_name}</a>
          </div>
          <div class="cluster-tags">
            {
              data.operations.map(item => <RenderOperationTag class="cluster-tag" data={item} />)
            }
            {
              !data.isOnline
                ? <db-icon svg type="yijinyong" class="cluster-tag" style="width: 38px; height: 16px;" />
                : null
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
      label: t('主访问入口'),
      field: 'master_domain',
      minWidth: 200,
      showOverflowTooltip: false,
      render: ({ data }: IColumn) => (
        <div class="domain">
          <span
            class="text-overflow"
            v-overflow-tips>
            {data.master_domain || '--'}
          </span>
          {
            data.master_domain && (
              <db-icon
                type="copy"
                v-bk-tooltips={t('复制主访问入口')}
                onClick={() => copy(data.master_domain)} />
            )
          }
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
            {data.slave_domain || '--'}
          </span>
          {
            data.slave_domain
            && (
              <db-icon
                type="copy"
                v-bk-tooltips={t('复制从访问入口')}
                onClick={() => copy(data.slave_domain)} />
            )
          }
        </div>
      ),
    },
    {
      label: t('MySQL版本'),
      field: 'version',
      width: 120,
      render: ({ data }: IColumn) => data.major_version,
    },
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
            data={data.spider_master}
            title={t('【inst】实例预览', {
              inst: data.master_domain, title: 'Spider Master',
            })}
            role="spider_master"
            clusterId={data.id}
            dataSource={getSpiderInstances}
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
            data={data.spider_slave}
            title={t('【inst】实例预览', {
              inst: data.master_domain, title: 'Spider slave',
            })}
            role="spider_slave"
            clusterId={data.id}
            dataSource={getSpiderInstances}
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
            data={data.spider_mnt}
            title={t('【inst】实例预览', {
              inst: data.master_domain, title: t('运维节点'),
            })}
            role="spider_mnt"
            clusterId={data.id}
            dataSource={getSpiderInstances}
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
            data={data.remote_db}
            title={t('【inst】实例预览', { inst: data.master_domain, title: 'RemoteDB' })}
            role="remote_master"
            clusterId={data.id}
            dataSource={getSpiderInstances}>
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
            data={data.remote_dr}
            title={t('【inst】实例预览', { inst: data.master_domain, title: 'RemoteDR' })}
            role="remote_slave"
            clusterId={data.id}
            dataSource={getSpiderInstances}>
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
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ data }: IColumn) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('创建时间'),
      field: 'create_at',
      width: 160,
      render: ({ data }: IColumn) => <span>{data.create_at || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      width: tableOperationWidth.value,
      fixed: props.isFullWidth ? 'right' : false,
      render: ({ data }: IColumn) => {
        const getOperations = (theme = 'primary') => {
          const operations = [
            <OperationStatusTips
              data={data}
              class="mr8">
              <bk-button
                text
                theme={theme}
                disabled={data.operationDisabled}
                class="mr-8"
                onClick={() => handleShowCapacityChange(data)}>
                { t('集群容量变更') }
              </bk-button>
            </OperationStatusTips>,
          ];
          if (!data.isOnline) {
            operations.push(...[
              <bk-button
                text
                theme={theme}
                class="mr-8"
                onClick={() => handleChangeClusterOnline(TicketTypes.TENDBCLUSTER_ENABLE, data)}>
                { t('启用') }
              </bk-button>,
              <bk-button
                text
                theme={theme}
                class="mr-8"
                onClick={() => handleDeleteCluster(data)}>
                { t('删除') }
              </bk-button>,
            ]);
          }
          return operations;
        };
        const getDropdownOperations = () => {
          const operations = [
            <bk-button
              text
              class="mr-8"
              onClick={() => handleShowScaleUp(data)}>
              { t('扩容接入层') }
            </bk-button>,
            <bk-button
              text
              class="mr-8"
              onClick={() => handleShowShrink(data)}>
              { t('缩容接入层') }
            </bk-button>,
          ];
          if (data.spider_mnt.length > 0) {
            operations.push(<bk-button
            text
            class="mr-8"
            onClick={() => handleRemoveMNT(data)}>
              { t('下架运维节点') }
            </bk-button>);
          }
          if (data.spider_slave.length > 0) {
            operations.push(<bk-button
              text
              class="mr-8"
              onClick={() => handleDestroySlave(data)}>
              { t('下架只读集群') }
            </bk-button>);
          }
          operations.push(<bk-button
            text
            class="mr-8"
            onClick={() => handleChangeClusterOnline(TicketTypes.TENDBCLUSTER_DISABLE, data)}>
            { t('禁用') }
          </bk-button>);

          return data.isOnline ? operations : [];
        };

        const renderDropdownOperations = [
          ...getDropdownOperations(),
        ];

        if (props.isFullWidth === false) {
          renderDropdownOperations.unshift(...getOperations(''));
        }

        return (
          <>
            {
              props.isFullWidth ? getOperations() : null
            }
            {
              renderDropdownOperations.length > 0
                ? (
                  <bk-dropdown class="operations-more">
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

  // 设置行样式
  const setRowClass = (row: TendbClusterModel) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === Number(route.query.cluster_id)) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['cluster_name', 'master_domain'].includes(item.field as string),
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key) as string[],
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

    console.log('from search');
    return Promise.resolve([]);
  };

  // 设置轮询
  useRequest(fetchTableData, {
    pollingInterval: 10000,
  });

  // 查看集群详情
  const handleToDetails = (row: TendbClusterModel) => {
    if (props.isFullWidth) {
      props.dragTrigger(true);
    }
    router.replace({
      query: { cluster_id: row.id },
    });
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
      },
    });
  };

  const handleTableSelected = ({ isAll, checked, data, row }: TableSelectionData<ResourceItem>) => {
    // 全选 checkbox 切换
    if (isAll) {
      selected.value = checked ? [...data] : [];
      return;
    }

    // 单选 checkbox 选中
    if (checked) {
      const toggleIndex = selected.value.findIndex(item => item.id === row.id);
      if (toggleIndex === -1) {
        selected.value.push(row);
      }
      return;
    }

    // 单选 checkbox 取消选中
    const toggleIndex = selected.value.findIndex(item => item.id === row.id);
    if (toggleIndex > -1) {
      selected.value.splice(toggleIndex, 1);
    }
  };

  // 批量授权
  const selected = ref<ResourceItem[]>([]);
  const hasSelected = computed(() => selected.value.length > 0);
  const clusterAuthorizeShow = ref(false);

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
</script>

<style lang="less" scoped>
.spider-manage-list-page {
  height: 100%;
  padding: 24px 0;
  margin: 0 24px;
  overflow: hidden;

  .operations {
    &.is-flex {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .bk-search-select {
        order: 2;
        flex: 1;
        max-width: 320px;
        margin-left: 8px;
      }
    }
  }

  .table-wrapper {
    background-color: white;

    .bk-table {
      height: 100% !important;
    }

    :deep(.bk-table-body) {
      max-height: calc(100% - 100px);
    }
  }

  .is-shrink-table {
    :deep(.bk-table-body) {
      overflow-x: hidden;
      overflow-y: auto;
    }
  }

  :deep(.cell) {
    line-height: normal !important;

    .domain {
      display: flex;
      align-items: center;
    }

    .db-icon-copy {
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
    .db-icon-copy {
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
</style>
