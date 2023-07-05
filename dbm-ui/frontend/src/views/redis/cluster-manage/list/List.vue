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
  <div class="redis-cluster">
    <div
      class="redis-cluster__operations"
      :class="{'is-flex': isFlexHeader}">
      <div class="redis-cluster__operations-right mb-16">
        <DbSearchSelect
          v-model="state.searchValues"
          :data="filterItems"
          :placeholder="$t('输入集群名_IP_域名关键字')"
          unique-select
          @change="handleFilter" />
      </div>
      <div class="redis-cluster__operations-left mb-16">
        <BkButton
          class="mr-8"
          theme="primary"
          @click="handleApply">
          {{ $t('申请实例') }}
        </BkButton>
        <BkDropdown
          v-bk-tooltips="{
            disabled: hasSelected,
            content: $t('请选择操作集群')
          }"
          class="redis-cluster__dropdown"
          :disabled="!hasSelected"
          @click.stop
          @hide="() => isShowDropdown = false"
          @show="() => isShowDropdown = true">
          <BkButton :disabled="!hasSelected">
            <span class="pr-4">{{ $t('批量操作') }}</span>
            <i
              class="db-icon-down-big redis-cluster__dropdown-icon"
              :class="[
                { 'redis-cluster__dropdown-icon--active': isShowDropdown }
              ]" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleShowExtract(state.selected)">
                {{ $t('提取Key') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handlShowDeleteKeys(state.selected)">
                {{ $t('删除Key') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleShowBackup(state.selected)">
                {{ $t('备份') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleShowPurge(state.selected)">
                {{ $t('清档') }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
    </div>
    <div
      v-bkloading="{ loading: state.isLoading, zIndex: 2 }"
      class="table-wrapper"
      :class="{'is-shrink-table': !isFullWidth}"
      :style="{ height: tableHeight }">
      <DbOriginalTable
        :key="tableKey"
        class="redis-cluster__table"
        :columns="columns"
        :data="state.data"
        :is-anomalies="state.isAnomalies"
        :is-row-select-enable="setRowSelectable"
        :is-searching="state.searchValues.length > 0"
        :pagination="renderPagination"
        remote-pagination
        :row-class="setRowClass"
        :settings="settings"
        @clear-search="handleClearSearch"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResources"
        @selection-change="handleTableSelected"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- 查看密码 -->
  <ClusterPassword
    v-model:is-show="passwordState.isShow"
    :fetch-params="passwordState.fetchParams" />
  <!-- 提取 keys -->
  <ExtractKeys
    v-model:is-show="extractState.isShow"
    :data="extractState.data" />
  <!-- 删除 keys -->
  <DeleteKeys
    v-model:is-show="deleteKeyState.isShow"
    :data="deleteKeyState.data" />
  <!-- 备份 -->
  <RedisBackup
    v-model:is-show="backupState.isShow"
    :data="backupState.data" />
  <!-- 清档 -->
  <RedisPurge
    v-model:is-show="purgeState.isShow"
    :data="purgeState.data" />
</template>

<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { createTicket } from '@services/ticket';
  import {
    ClusterNodeKeys,
    type ResourceRedisItem,
  } from '@services/types/clusters';

  import { useDefaultPagination, useInfoWithIcon, useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    DBTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';

  import type { RedisState } from '@views/redis/common/types';

  import { isRecentDays, messageWarn, random } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import { useRedisData } from '../hooks/useRedisData';

  import RedisBackup from './components/Backup.vue';
  import ClusterPassword from './components/ClusterPassword.vue';
  import DeleteKeys from './components/DeleteKeys.vue';
  import ExtractKeys from './components/ExtractKeys.vue';
  import OperationStatusTips from './components/OperationStatusTips.vue';
  import RedisPurge from './components/Purge.vue';
  import RenderOperationTag from './components/RenderOperationTag.vue';

  import type { TableColumnRender, TableSelectionData } from '@/types/bkui-vue';

  type ColumnRenderData = { data: ResourceRedisItem }

  interface Props {
    width: number,
    isFullWidth: boolean,
    dragTrigger: (isLeft: boolean) => void
  }

  const props = defineProps<Props>();

  const { t, locale } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const tableKey = ref(random());
  const isCN = computed(() => locale.value === 'zh-cn');
  const isFlexHeader = computed(() => props.width >= 460);
  const tableHeight = computed(() => `calc(100% - ${isFlexHeader.value ? 48 : 96}px)`);
  const disabledOperations: string[] = [TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_CLOSE];
  const tableOperationWidth = computed(() => {
    if (props.isFullWidth) {
      return isCN.value ? 240 : 300;
    }
    return 60;
  });
  const columns = computed<InstanceType<typeof Table>['$props']['columns']>(() => [{
    type: 'selection',
    width: 54,
    label: '',
    fixed: 'left',
  }, {
    label: 'ID',
    field: 'id',
    fixed: 'left',
    width: 100,
  }, {
    label: t('集群名称'),
    field: 'name',
    minWidth: 200,
    fixed: 'left',
    showOverflowTooltip: false,
    render: ({ data }: ColumnRenderData) => (
      <div class="cluster-name-container">
        <div
          class="cluster-name text-overflow"
          v-overflow-tips={{
            content: `<p>${t('集群名称')}：${data.cluster_name}</p><p>${t('集群别名')}：${data.cluster_alias}</p>`,
            allowHTML: true,
          }}
        >
          <a href="javascript:" onClick={() => handleToDetails(data)}>{data.cluster_name}</a><br />
          <span class="cluster-name__alias">{data.cluster_alias}</span>
        </div>
        <div class="cluster-tags">
          {
            data.operations.map(item => <RenderOperationTag class="cluster-tag" data={item} />)
          }
          {
            data.phase === 'offline'
              ? <db-icon svg type="yijinyong" class="cluster-tag" style="width: 38px; height: 16px;" />
              : null
          }
          {
            isRecentDays(data.create_at, 24 * 3)
              ? <span class="glob-new-tag cluster-tag ml-4" data-text="NEW" />
              : null
          }
        </div>
      </div>
    ),
  }, {
    label: t('管控区域'),
    field: 'bk_cloud_name',
  }, {
    label: t('状态'),
    field: 'status',
    width: 100,
    render: ({ data }: ColumnRenderData) => {
      const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
      return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
    },
  }, {
    label: t('域名'),
    field: 'master_domain',
    minWidth: 200,
  }, {
    label: 'Proxy',
    field: ClusterNodeKeys.PROXY,
    minWidth: 230,
    showOverflowTooltip: false,
    render: ({ data }: ColumnRenderData) => (
      <RenderInstances
        data={data[ClusterNodeKeys.PROXY]}
        title={t('【inst】实例预览', { title: 'Proxy', inst: data.master_domain })}
        role={ClusterNodeKeys.PROXY}
        clusterId={data.id}
        dbType={DBTypes.REDIS}
      />
    ),
  }, {
    label: 'Master',
    field: ClusterNodeKeys.REDIS_MASTER,
    minWidth: 230,
    showOverflowTooltip: false,
    render: ({ data }: ColumnRenderData) => (
      <RenderInstances
        data={data[ClusterNodeKeys.REDIS_MASTER]}
        title={t('【inst】实例预览', { title: 'Master', inst: data.master_domain })}
        role={ClusterNodeKeys.REDIS_MASTER}
        clusterId={data.id}
        dbType={DBTypes.REDIS}
      />
    ),
  }, {
    label: 'Slave',
    field: ClusterNodeKeys.REDIS_SLAVE,
    minWidth: 230,
    showOverflowTooltip: false,
    render: ({ data }: ColumnRenderData) => (
      <RenderInstances
        data={data[ClusterNodeKeys.REDIS_SLAVE]}
        title={t('【inst】实例预览', { title: 'Slave', inst: data.master_domain })}
        role={ClusterNodeKeys.REDIS_SLAVE}
        clusterId={data.id}
        dbType={DBTypes.REDIS}
      />
    ),
  }, {
    label: t('架构版本'),
    field: 'cluster_type_name',
    minWidth: 160,
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('更新人'),
    field: 'updater',
    width: 140,
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('更新时间'),
    field: 'update_at',
    width: 160,
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('创建人'),
    field: 'creator',
    width: 140,
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('创建时间'),
    field: 'create_at',
    width: 160,
    render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
  }, {
    label: t('操作'),
    field: '',
    width: tableOperationWidth.value,
    fixed: props.isFullWidth ? 'right' : false,
    render: ({ data }: ColumnRenderData) => {
      const getOperations = (theme = 'primary') => {
        const baseOperations = [
          <OperationStatusTips
            clusterStatus={data.status}
            data={data.operations[0]}
            disabledList={disabledOperations}>
            {{
              default: ({ disabled }: { disabled: boolean }) => (
                <bk-button
                  disabled={disabled || data.phase === 'offline'}
                  text
                  theme={theme}
                  onClick={() => handleShowBackup([data])}>
                  { t('备份') }
                </bk-button>
              ),
            }}
          </OperationStatusTips>,
          <OperationStatusTips
            clusterStatus={data.status}
            data={data.operations[0]}
            disabledList={disabledOperations}>
            {{
              default: ({ disabled }: { disabled: boolean }) => (
                <bk-button
                  disabled={disabled || data.phase === 'offline'}
                  text
                  theme={theme}
                  onClick={() => handleShowPurge([data])}>
                  { t('清档') }
                </bk-button>
              ),
            }}
          </OperationStatusTips>,
        ];
        if (data.bk_cloud_id > 0) {
          return [
            <span v-bk-tooltips={t('暂不支持跨管控区域提取Key')}>
              <bk-button text theme={theme} disabled>{t('提取Key')}</bk-button>
            </span>,
            <span v-bk-tooltips={t('暂不支持跨管控区域删除Key')}>
              <bk-button text theme={theme} disabled>{ t('删除Key') }</bk-button>
            </span>,
            ...baseOperations,
          ];
        }
        return [
          <OperationStatusTips
            clusterStatus={data.status}
            data={data.operations[0]}
            disabledList={disabledOperations}>
            {{
              default: ({ disabled }: { disabled: boolean }) => (
                <bk-button
                  disabled={disabled || data.phase === 'offline'}
                  text
                  theme={theme}
                  onClick={() => handleShowExtract([data])}>
                  {t('提取Key')}
                </bk-button>
              ),
            }}
          </OperationStatusTips>,
          <OperationStatusTips
            clusterStatus={data.status}
            data={data.operations[0]}
            disabledList={disabledOperations}>
            {{
              default: ({ disabled }: { disabled: boolean }) => (
                <bk-button
                  disabled={disabled || data.phase === 'offline'}
                  text
                  theme={theme}
                  onClick={() => handlShowDeleteKeys([data])}>
                  { t('删除Key') }
                </bk-button>
              ),
            }}
          </OperationStatusTips>,
          ...baseOperations,
        ];
      };
      const getDropdownOperations = () => (
        <>
          <bk-dropdown-item>
            <OperationStatusTips
              clusterStatus={data.status}
              data={data.operations[0]}
              disabledList={[TicketTypes.REDIS_DESTROY]}>
              {{
                default: ({ disabled }: { disabled: boolean }) => (
                  <bk-button style="width: 100%;height: 32px; justify-content: flex-start;" disabled={disabled} text onClick={() => handleShowPassword(data.id)}>{ t('获取访问方式') }</bk-button>
                ),
              }}
            </OperationStatusTips>
          </bk-dropdown-item>
          {
            data.phase === 'online'
              ? (
                <bk-dropdown-item>
                  <OperationStatusTips
                    clusterStatus={data.status}
                    data={data.operations[0]}
                    disabledList={[TicketTypes.REDIS_PROXY_CLOSE]}>
                    {{
                      default: ({ disabled }: { disabled: boolean }) => (
                        <bk-button
                          style="width: 100%;height: 32px; justify-content: flex-start;"
                          disabled={disabled}
                          text
                          onClick={() => handleSwitchRedis(TicketTypes.REDIS_PROXY_CLOSE, data)}>
                          { t('禁用') }
                        </bk-button>
                      ),
                    }}
                  </OperationStatusTips>
                </bk-dropdown-item>
              ) : null
          }
          {
            data.phase === 'offline'
              ? [
                <bk-dropdown-item>
                  <OperationStatusTips
                    clusterStatus={data.status}
                    data={data.operations[0]}
                    disabledList={[TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_OPEN]}>
                    {{
                      default: ({ disabled }: { disabled: boolean }) => (
                        <bk-button
                          style="width: 100%;height: 32px; justify-content: flex-start;"
                          disabled={disabled}
                          text
                          onClick={() => handleSwitchRedis(TicketTypes.REDIS_PROXY_OPEN, data)}>
                          { t('启用') }
                        </bk-button>
                      ),
                    }}
                  </OperationStatusTips>
                </bk-dropdown-item>,
                <bk-dropdown-item>
                  <OperationStatusTips
                    clusterStatus={data.status}
                    data={data.operations[0]}
                    disabledList={[TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_OPEN]}>
                    {{
                      default: ({ disabled }: { disabled: boolean }) => (
                        <bk-button
                          style="width: 100%;height: 32px; justify-content: flex-start;"
                          disabled={disabled}
                          text
                          onClick={() => handleDeleteCluster(data)}>
                          { t('删除') }
                        </bk-button>
                      ),
                    }}
                  </OperationStatusTips>
                </bk-dropdown-item>,
              ] : null
          }
        </>
      );
      if (props.isFullWidth) {
        return (
          <div class="operations">
            {getOperations()}
            <bk-dropdown class="operations__more">
              {{
                default: () => <i class="db-icon-more"></i>,
                content: () => (
                  <bk-dropdown-menu>
                    {getDropdownOperations()}
                  </bk-dropdown-menu>
                ),
              }}
            </bk-dropdown>
          </div>
        );
      }
      return (
        <bk-dropdown class="operations__more">
          {{
            default: () => <i class="db-icon-more"></i>,
            content: () => (
              <bk-dropdown-menu>
                {
                  getOperations('').map(opt => <bk-dropdown-item>{opt}</bk-dropdown-item>)
                }
                {getDropdownOperations()}
              </bk-dropdown-menu>
            ),
          }}
        </bk-dropdown>
      );
    },
  }]);

  watch(() => props.isFullWidth, () => {
    tableKey.value = random();
  });

  // 设置行样式
  const setRowClass = (row: ResourceRedisItem) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === Number(route.query.cluster_id)) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };
  const setRowSelectable = ({ row }: { row: ResourceRedisItem }) => {
    if (row.phase === 'offline') return false;

    if (row.operations?.length > 0) {
      const operationData = row.operations[0];
      return !disabledOperations.includes(operationData.ticket_type);
    }

    return true;
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['name', 'master_domain'].includes(item.field as string),
    })),
    checked: [
      'id',
      'bk_cloud_name',
      'name',
      'master_domain',
      'creator',
      'create_at',
      ClusterNodeKeys.PROXY,
      ClusterNodeKeys.REDIS_MASTER,
      ClusterNodeKeys.REDIS_SLAVE,
    ],
    showLineHeight: false,
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.REDIS_TABLE_SETTINGS, defaultSettings);

  const isShowDropdown = ref(false);
  const state = reactive<RedisState>({
    isInit: true,
    isAnomalies: false,
    isLoading: false,
    data: [],
    selected: [],
    searchValues: [],
    pagination: useDefaultPagination(),
  });

  const renderPagination = computed(() => {
    if (props.isFullWidth) {
      return { ...state.pagination };
    }
    return {
      ...state.pagination,
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });
  const hasSelected = computed(() => state.selected.length > 0);
  const filterItems = [{
    name: t('集群名'),
    id: 'name',
  }, {
    name: t('域名'),
    id: 'domain',
  }, {
    name: 'IP',
    id: 'ip',
  }];

  /** 列表基础操作方法 */
  const {
    fetchResources,
    handeChangeLimit,
    handleChangePage,
    handleFilter,
  } = useRedisData(state);

  const handleClearSearch = () => {
    state.searchValues = [];
    handleChangePage(1);
  };

  // 设置轮询
  const { pause, resume } = useTimeoutPoll(() => {
    fetchResources({}, state.isInit);
  }, 5000);
  onMounted(() => {
    resume();
  });
  onBeforeUnmount(() => {
    pause();
  });

  /**
   * 申请实例
   */
  function handleApply() {
    router.push({
      name: 'SelfServiceApplyRedis',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  }

  /**
   * 查看集群详情
   */
  function handleToDetails(data: ResourceRedisItem) {
    if (props.isFullWidth) {
      props.dragTrigger(true);
    }
    router.replace({
      query: { cluster_id: data.id },
    });
  }

  /**
   * 表格选中
   */
  function handleTableSelected({ isAll, checked, data, row }: TableSelectionData<ResourceRedisItem>) {
    // 全选 checkbox 切换
    if (isAll) {
      const filterData = data.filter(item => item.phase === 'online');
      state.selected = checked ? [...filterData] : [];
      return;
    }

    // 单选 checkbox 选中
    if (checked) {
      const toggleIndex = state.selected.findIndex(item => item.id === row.id);
      if (toggleIndex === -1) {
        state.selected.push(row);
      }
      return;
    }

    // 单选 checkbox 取消选中
    const toggleIndex = state.selected.findIndex(item => item.id === row.id);
    if (toggleIndex > -1) {
      state.selected.splice(toggleIndex, 1);
    }
  }

  /** 查看密码 */
  const passwordState = reactive({
    isShow: false,
    fetchParams: {
      cluster_id: -1,
      bk_biz_id: globalBizsStore.currentBizId,
      db_type: DBTypes.REDIS,
      type: DBTypes.REDIS,
    },
  });
  function handleShowPassword(id: number) {
    passwordState.isShow = true;
    passwordState.fetchParams.cluster_id = id;
  }

  /** 提取 key 功能 */
  const extractState = reactive({
    isShow: false,
    data: [] as ResourceRedisItem[],
  });
  function handleShowExtract(data: ResourceRedisItem[] = []) {
    if (
      data.some(item => item.operations.length > 0
        && item.operations.map(op => op.ticket_type).includes(TicketTypes.REDIS_DESTROY))
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    if (data.some(item => item.bk_cloud_id > 0)) {
      messageWarn(t('暂不支持跨管控区域提取Key'));
      return;
    }
    extractState.isShow = true;
    extractState.data = _.cloneDeep(data);
  }

  /** 删除 key 功能 */
  const deleteKeyState = reactive({
    isShow: false,
    data: [] as ResourceRedisItem[],
  });
  function handlShowDeleteKeys(data: ResourceRedisItem[] = []) {
    if (
      data.some(item => item.operations.length > 0
        && item.operations.map(op => op.ticket_type).includes(TicketTypes.REDIS_DESTROY))
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    if (data.some(item => item.bk_cloud_id > 0)) {
      messageWarn(t('暂不支持跨管控区域删除Key'));
      return;
    }
    deleteKeyState.isShow = true;
    deleteKeyState.data = _.cloneDeep(data);
  }

  /** 备份功能 */
  const backupState = reactive({
    isShow: false,
    data: [] as ResourceRedisItem[],
  });
  function handleShowBackup(data: ResourceRedisItem[] = []) {
    if (
      data.some(item => item.operations.length > 0
        && item.operations.map(op => op.ticket_type).includes(TicketTypes.REDIS_DESTROY))
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    backupState.isShow = true;
    backupState.data = _.cloneDeep(data);
  }

  /** 清档功能 */
  const purgeState = reactive({
    isShow: false,
    data: [] as ResourceRedisItem[],
  });
  function handleShowPurge(data: ResourceRedisItem[] = []) {
    if (
      data.some(item => item.operations.length > 0
        && item.operations.map(op => op.ticket_type).includes(TicketTypes.REDIS_DESTROY))
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    purgeState.isShow = true;
    purgeState.data = _.cloneDeep(data);
  }

  /**
   * 集群启停
   */
  function handleSwitchRedis(type: TicketTypesStrings, data: ResourceRedisItem) {
    if (!type) return;

    const isOpen = type === TicketTypes.REDIS_PROXY_OPEN;
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
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: type,
            details: {
              cluster_id: data.id,
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }

  /**
   * 删除集群
   */
  function handleDeleteCluster(data: ResourceRedisItem) {
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
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: TicketTypes.REDIS_DESTROY,
            details: {
              cluster_id: data.id,
            },
          };
          await createTicket(params)
            .then((res) => {
              ticketMessage(res.id);
            });
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .redis-cluster {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    &__operations {
      &.is-flex {
        display: flex;
        align-items: center;
        justify-content: space-between;

        .redis-cluster__operations-right {
          order: 2;
          flex: 1;
          max-width: 320px;
          margin-left: 8px;
        }
      }
    }

    &__dropdown {
      &-icon {
        color: @gray-color;
        transform: rotate(0);
        transition: all 0.2s;

        &--active {
          transform: rotate(-90deg);
        }
      }
    }

    .table-wrapper {
      background-color: white;

      .bk-table {
        height: 100%;
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

    &__table {
      :deep(.cell) {
        line-height: unset !important;
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
          margin-left: 8px;
          align-items: center;
          flex-wrap: wrap;
        }

        .cluster-tag {
          flex-shrink: 0;
          margin: 2px 0;
        }
      }

      :deep(.ip-list) {
        padding: 8px 0;

        &__more {
          display: inline-block;
          margin-top: 2px;
        }

        .db-icon-copy {
          display: none;
          margin-top: 1px;
          margin-left: 8px;
          color: @primary-color;
          vertical-align: text-top;
          cursor: pointer;
        }
      }

      :deep(.operations) {
        .bk-button {
          margin-right: 8px;
        }

        &__more {
          .db-icon-more {
            display: block;
            font-size: @font-size-normal;
            font-weight: bold;
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
          display: inline-block;
        }
      }

      :deep(.is-offline) {
        .cluster-name-container {
          .cluster-name {
            a {
              color: @gray-color;
            }

            &__alias {
              color: @disable-color;
            }
          }
        }

        .cell {
          color: @disable-color;
        }
      }
    }
  }
</style>
