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
  <div class="redis-cluster-list-page">
    <div class="operation-box">
      <div>
        <AuthButton
          action-id="redis_cluster_apply"
          class="mr-8 mb-16"
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </AuthButton>
        <BkDropdown
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择操作集群'),
          }"
          class="cluster-dropdown mb-16"
          :disabled="!hasSelected"
          @click.stop
          @hide="() => (isShowDropdown = false)"
          @show="() => (isShowDropdown = true)">
          <BkButton :disabled="!hasSelected">
            <span class="pr-4">{{ t('批量操作') }}</span>
            <DbIcon
              class="cluster-dropdown-icon"
              :class="[{ 'cluster-dropdown-icon-active': isShowDropdown }]"
              type="down-big " />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleShowExtract(state.selected)">
                {{ t('提取Key') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handlShowDeleteKeys(state.selected)">
                {{ t('删除Key') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleShowBackup(state.selected)">
                {{ t('备份') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleShowPurge(state.selected)">
                {{ t('清档') }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
        <DropdownExportExcel
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="redis" />
      </div>
      <DbSearchSelect
        v-model="searchValue"
        class="operations-right mb-16"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select />
    </div>
    <div class="table-wrapper-out">
      <div
        class="table-wrapper"
        :class="{ 'is-shrink-table': isStretchLayoutOpen }">
        <DbTable
          ref="tableRef"
          :columns="columns"
          :data-source="getRedisList"
          :disable-select-method="disableSelectMethod"
          :pagination-extra="paginationExtra"
          releate-url-query
          :row-class="getRowClass"
          selectable
          :settings="settings"
          @clear-search="clearSearchValue"
          @column-filter="columnFilterChange"
          @column-sort="columnSortChange"
          @selection="handleSelection"
          @setting-change="updateTableSettings" />
      </div>
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
  <EditEntryConfig
    :id="clusterId"
    v-model:is-show="showEditEntryConfig"
    :get-detail-info="getRedisDetail" />
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import {
    getRedisDetail,
    getRedisInstances,
    getRedisList,
  } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';
  import {
    ClusterNodeKeys,
  } from '@services/types/clusters';

  import {
    useCopy,
    useInfoWithIcon,
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import {
    useGlobalBizs,
  } from '@stores';

  import {
    ClusterTypes,
    DBTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import EditEntryConfig from '@components/cluster-entry-config/Index.vue';
  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    messageWarn,
  } from '@utils';

  import RedisBackup from './components/Backup.vue';
  import ClusterPassword from './components/ClusterPassword.vue';
  import DeleteKeys from './components/DeleteKeys.vue';
  import EntryPanel from './components/EntryPanel.vue';
  import ExtractKeys from './components/ExtractKeys.vue';
  import RedisPurge from './components/Purge.vue';

  import type {
    SearchSelectData,
    SearchSelectItem,
    TableColumnRender,
  } from '@/types/bkui-vue';

  interface RedisState {
    selected: RedisModel[]
  }

  type ColumnRenderData = { data: RedisModel }

  const clusterId = defineModel<number>('clusterId');

  const { t, locale } = useI18n();
  const copy = useCopy();
  const route = useRoute();
  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
  } = useLinkQueryColumnSerach(ClusterTypes.REDIS, [
    'bk_cloud_id',
    'major_version',
    'region',
    'time_zone',
  ], () => fetchData(isInit));

  const disabledOperations: string[] = [TicketTypes.REDIS_DESTROY, TicketTypes.REDIS_PROXY_CLOSE];

  const tableRef = ref();
  const isShowDropdown = ref(false);
  const showEditEntryConfig = ref(false);

  const state = reactive<RedisState>({
    selected: [],
  });

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

  /** 提取 key 功能 */
  const extractState = reactive({
    isShow: false,
    data: [] as RedisModel[],
  });

  /** 删除 key 功能 */
  const deleteKeyState = reactive({
    isShow: false,
    data: [] as RedisModel[],
  });

  /** 备份功能 */
  const backupState = reactive({
    isShow: false,
    data: [] as RedisModel[],
  });

  /** 清档功能 */
  const purgeState = reactive({
    isShow: false,
    data: [] as RedisModel[],
  });

  const searchSelectData = computed(() => [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: 'IP',
      id: 'ip',
    },
    {
      name: t('实例'),
      id: 'instance',
    },
    {
      name: t('访问入口'),
      id: 'domain',
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
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
    },
    {
      name: t('版本'),
      id: 'major_version',
      multiple: true,
      children: searchAttrs.value.major_version,
    },
    {
      name: t('地域'),
      id: 'region',
      multiple: true,
      children: searchAttrs.value.region,
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ] as SearchSelectData);

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
  const hasSelected = computed(() => state.selected.length > 0);
  const selectedIds = computed(() => state.selected.map(item => item.id));
  const isCN = computed(() => locale.value === 'zh-cn');
  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 240 : 320;
    }
    return 60;
  });

  const searchIp = computed<string[]>(() => {
    const ipObj = searchValue.value.find(item => item.id === 'ip');
    if (ipObj && ipObj.values) {
      return [ipObj.values[0].id];
    }
    return [];
  });

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 60,
    },
    {
      label: t('访问入口'),
      field: 'master_domain',
      width: 300,
      minWidth: 300,
      fixed: 'left',
      render: ({ data }: ColumnRenderData) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="redis_view"
                resource={data.id}
                permission={data.permission.redis_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.masterDomainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                {data.isOnlineCLB && (
                  <EntryPanel
                    entryType='clb'
                    clusterId={data.id}>
                      <MiniTag
                        content="CLB"
                        extCls='redis-manage-clb-minitag' />
                  </EntryPanel>
                )}
                {data.isOnlinePolaris && (
                  <EntryPanel
                    entryType='polaris'
                    clusterId={data.id}
                    panelWidth={418}>
                    <MiniTag
                      content="北极星"
                      extCls='redis-manage-polary-minitag' />
                  </EntryPanel>
                )}
                {data.master_domain && (
                  <db-icon
                    type="copy"
                    v-bk-tooltips={t('复制访问入口')}
                    onClick={() => copy(data.masterDomainDisplayName)} />
                )}
                <auth-button
                  v-bk-tooltips={t('修改入口配置')}
                  action-id="access_entry_edit"
                  resource="redis"
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
            }}>
            <span>
              {data.cluster_name}
            </span>
            <p class="cluster-name__alias">
              {data.cluster_alias || '--'}
            </p>
          </div>
          <div class="cluster-tags">
            {
              data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag" data={item} />)
            }
            {
              !data.isOnline && !data.isStarting && (
                <db-icon
                  svg
                  type="yijinyong"
                  class="cluster-tag"
                  style="width: 38px; height: 16px;" />
              )
            }
            {
              data.isNew && (
                <span
                  class="glob-new-tag cluster-tag ml-4"
                  data-text="NEW" />
              )
            }
          </div>
          <db-icon
            v-bk-tooltips={t('复制集群名称')}
            class="mt-4"
            type="copy"
            onClick={() => copy(data.cluster_name)} />
        </div>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
      },
    },
    {
      label: t('状态'),
      field: 'status',
      width: 100,
      filter: {
        list: [
          {
            value: 'normal',
            text: t('正常'),
          },
          {
            value: 'abnormal',
            text: t('异常'),
          },
        ],
      },
      render: ({ data }: ColumnRenderData) => {
        const info = data.status === 'normal'
          ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return (
          <DbStatus theme={info.theme}>
            {info.text}
          </DbStatus>
        );
      },
    },
    {
      label: 'Proxy',
      field: ClusterNodeKeys.PROXY,
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: ColumnRenderData) => (
        <RenderInstances
          highlightIps={searchIp.value}
          data={data[ClusterNodeKeys.PROXY]}
          title={t('【inst】实例预览', { title: 'Proxy', inst: data.master_domain })}
          role={ClusterNodeKeys.PROXY}
          clusterId={data.id}
          dataSource={getRedisInstances}
        />
      ),
    },
    {
      label: 'Master',
      field: ClusterNodeKeys.REDIS_MASTER,
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: ColumnRenderData) => (
        <RenderInstances
          highlightIps={searchIp.value}
          data={data[ClusterNodeKeys.REDIS_MASTER]}
          title={t('【inst】实例预览', { title: 'Master', inst: data.master_domain })}
          role={ClusterNodeKeys.REDIS_MASTER}
          clusterId={data.id}
          dataSource={getRedisInstances}
        />
      ),
    },
    {
      label: 'Slave',
      field: ClusterNodeKeys.REDIS_SLAVE,
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: ColumnRenderData) => (
        <RenderInstances
          highlightIps={searchIp.value}
          data={data[ClusterNodeKeys.REDIS_SLAVE]}
          title={t('【inst】实例预览', { title: 'Slave', inst: data.master_domain })}
          role={ClusterNodeKeys.REDIS_SLAVE}
          clusterId={data.id}
          dataSource={getRedisInstances}
        />
      ),
    },
    {
      label: t('架构版本'),
      field: 'cluster_type_name',
      minWidth: 160,
      render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
      },
      render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
      },
      render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 140,
      render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 160,
      render: ({ data }: ColumnRenderData) => <span>{data.updateAtDisplay || '--'}</span>,
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      sort: true,
      width: 160,
      render: ({ data }: ColumnRenderData) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
      },
      render: ({ cell }: TableColumnRender) => <span>{cell || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: ColumnRenderData) => {
        const getOperations = (theme = 'primary') => {
          const baseOperations = [
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                action-id="redis_backup"
                resource={data.id}
                permission={data.permission.redis_backup}
                disabled={data.isOffline}
                text
                theme={theme}
                onClick={() => handleShowBackup([data])}>
                { t('备份') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                action-id="redis_purge"
                resource={data.id}
                permission={data.permission.redis_purge}
                disabled={data.isOffline}
                text
                theme={theme}
                onClick={() => handleShowPurge([data])}>
                { t('清档') }
              </auth-button>
            </OperationBtnStatusTips>,
          ];
          if (data.bk_cloud_id > 0) {
            return [
              <span v-bk-tooltips={t('暂不支持跨管控区域提取Key')}>
                <auth-button
                  action-id="redis_keys_extract"
                  resource={data.id}
                  permission={data.permission.redis_keys_extract}
                  text
                  theme={theme}
                  disabled>
                  {t('提取Key')}
                </auth-button>
              </span>,
              <span v-bk-tooltips={t('暂不支持跨管控区域删除Key')}>
                <auth-button
                  action-id="redis_keys_delete"
                  resource={data.id}
                  permission={data.permission.redis_keys_delete}
                  text
                  theme={theme}
                  disabled>
                  { t('删除Key') }
                </auth-button>
              </span>,
              ...baseOperations,
            ];
          }
          return [
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                action-id="redis_keys_extract"
                resource={data.id}
                permission={data.permission.redis_keys_extract}
                disabled={data.isOffline}
                text
                theme={theme}
                onClick={() => handleShowExtract([data])}>
                {t('提取Key')}
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips
              data={data}
              disabled={!data.isOffline}>
              <auth-button
                action-id="redis_keys_delete"
                resource={data.id}
                permission={data.permission.redis_keys_delete}
                disabled={data.isOffline}
                text
                theme={theme}
                onClick={() => handlShowDeleteKeys([data])}>
                { t('删除Key') }
              </auth-button>
            </OperationBtnStatusTips>,
            ...baseOperations,
          ];
        };

        return (
            <div class="operations">
              {getOperations()}
              <bk-dropdown
                class="operations__more"
                trigger="click"
                popover-options={{ zIndex: 10 }}>
                {{
                  default: () => <db-icon type="more" />,
                  content: () => (
                    <bk-dropdown-menu>
                      <bk-dropdown-item>
                        <OperationBtnStatusTips
                        data={data}
                        disabled={!data.isOffline}>
                          <auth-button
                            action-id="access_entry_edit"
                            resource={data.id}
                            permission={data.permission.access_entry_edit}
                            style="width: 100%;height: 32px;"
                            disabled={data.isOffline}
                            text
                            onClick={() => handleShowPassword(data.id)}>
                            { t('获取访问方式') }
                          </auth-button>
                        </OperationBtnStatusTips>
                      </bk-dropdown-item>
                      <fun-controller moduleId="addons" controllerId="redis_nameservice">
                        <bk-dropdown-item>
                          <OperationBtnStatusTips
                            data={data}
                            disabled={!data.isOffline}>
                            <bk-button
                              style="width: 100%;height: 32px;"
                              disabled={data.isOffline}
                              text
                              onClick={() => handleSwitchCLB(data)}>
                              { data.isOnlineCLB ? t('禁用CLB') : t('启用CLB') }
                            </bk-button>
                          </OperationBtnStatusTips>
                        </bk-dropdown-item>
                        <bk-dropdown-item>
                          <OperationBtnStatusTips
                            data={data}
                            disabled={!data.isOffline}>
                            <bk-button
                              style="width: 100%;height: 32px;"
                              disabled={data.isOffline}
                              text
                              onClick={() => handleSwitchDNSBindCLB(data)}>
                              { data.dns_to_clb ? t('恢复DNS域名指向') : t('DNS域名指向CLB') }
                            </bk-button>
                          </OperationBtnStatusTips>
                        </bk-dropdown-item>
                        <bk-dropdown-item>
                          <OperationBtnStatusTips
                            data={data}
                            disabled={!data.isOffline}>
                            <bk-button
                              style="width: 100%;height: 32px;"
                              disabled={data.isOffline}
                              text
                              onClick={() => handleSwitchPolaris(data)}>
                              { data.isOnlinePolaris ? t('禁用北极星') : t('启用北极星') }
                            </bk-button>
                          </OperationBtnStatusTips>
                        </bk-dropdown-item>
                      </fun-controller>
                      {
                        data.isOnline && (
                          <bk-dropdown-item>
                            <OperationBtnStatusTips data={data}>
                              <auth-button
                                action-id="redis_open_close"
                                resource={data.id}
                                permission={data.permission.redis_open_close}
                                style="width: 100%;height: 32px;"
                                disabled={data.operationDisabled}
                                text
                                onClick={() => handleSwitchRedis(TicketTypes.REDIS_PROXY_CLOSE, data)}>
                                { t('禁用') }
                              </auth-button>
                            </OperationBtnStatusTips>
                          </bk-dropdown-item>
                        )
                      }
                      {
                        !data.isOnline && (
                          <bk-dropdown-item>
                            <OperationBtnStatusTips data={data}>
                              <auth-button
                                action-id="redis_open_close"
                                resource={data.id}
                                permission={data.permission.redis_open_close}
                                style="width: 100%;height: 32px;"
                                text
                                disabled={data.isStarting}
                                onClick={() => handleSwitchRedis(TicketTypes.REDIS_PROXY_OPEN, data)}>
                                { t('启用') }
                              </auth-button>
                            </OperationBtnStatusTips>
                          </bk-dropdown-item>
                        )
                      }
                      {
                        data.isOffline && (
                          <bk-dropdown-item>
                            <OperationBtnStatusTips data={data}>
                              <auth-button
                                action-id="redis_destroy"
                                resource={data.id}
                                permission={data.permission.redis_destroy}
                                style="width: 100%;height: 32px;"
                                disabled={Boolean(data.operationTicketId)}
                                text
                                onClick={() => handleDeleteCluster(data)}>
                                { t('删除') }
                              </auth-button>
                            </OperationBtnStatusTips>
                          </bk-dropdown-item>
                        )
                      }
                    </bk-dropdown-menu>
                  ),
                }}
              </bk-dropdown>
            </div>
        );
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['master_domain'].includes(item.field as string),
    })),
    checked: [
      'bk_cloud_name',
      'name',
      'master_domain',
      'creator',
      'create_at',
      'major_version',
      'region',
      'cluster_time_zone',
      ClusterNodeKeys.PROXY,
      ClusterNodeKeys.REDIS_MASTER,
      ClusterNodeKeys.REDIS_SLAVE,
    ],
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.REDIS_TABLE_SETTINGS, defaultSettings);

  const getMenuList = async (item: SearchSelectItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  const getRowClass = (data: RedisModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = data.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const disableSelectMethod = (data: RedisModel) => {
    if (!data.isOnline) {
      return true;
    }

    if (data.operations?.length > 0) {
      const operationData = data.operations[0];
      return disabledOperations.includes(operationData.ticket_type);
    }

    return false;
  };

  let isInit = true;
  const fetchData = (loading?:boolean) => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData(params, {
      ...sortValue,
    }, loading);
    isInit = false;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyRedis',
      query: {
        bizId: globalBizsStore.currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleSelection = (data: RedisModel, list: RedisModel[]) => {
    state.selected = list;
  };

  /**
   * 查看集群详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  const handleOpenEntryConfig = (row: RedisModel) => {
    showEditEntryConfig.value  = true;
    clusterId.value = row.id;
  };

  const handleShowPassword = (id: number) => {
    passwordState.isShow = true;
    passwordState.fetchParams.cluster_id = id;
  };

  const handleShowExtract = (data: RedisModel[] = []) => {
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
  };

  const handlShowDeleteKeys = (data: RedisModel[] = []) => {
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
  };

  const handleShowBackup = (data: RedisModel[] = []) => {
    if (
      data.some(item => item.operations.length > 0
        && item.operations.map(op => op.ticket_type).includes(TicketTypes.REDIS_DESTROY))
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    backupState.isShow = true;
    backupState.data = _.cloneDeep(data);
  };

  const handleShowPurge = (data: RedisModel[] = []) => {
    if (
      data.some(item => item.operations.length > 0
        && item.operations.map(op => op.ticket_type).includes(TicketTypes.REDIS_DESTROY))
    ) {
      messageWarn(t('选中集群存在删除中的集群无法操作'));
      return;
    }
    purgeState.isShow = true;
    purgeState.data = _.cloneDeep(data);
  };

  /**
   * 集群启停
   */
  const handleSwitchRedis = (type: TicketTypesStrings, data: RedisModel) => {
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
  };

  /**
   * 集群 CLB 启用/禁用
   */
  const handleSwitchCLB = (data: RedisModel) => {
    const ticketType = data.isOnlineCLB
      ? TicketTypes.REDIS_PLUGIN_DELETE_CLB
      : TicketTypes.REDIS_PLUGIN_CREATE_CLB;

    const title = ticketType === TicketTypes.REDIS_PLUGIN_CREATE_CLB ? t('确定启用CLB？') : t('确定禁用CLB？');

    InfoBox({
      title,
      subTitle: t('启用 CLB 之后，该集群可以通过 CLB 来访问'),
      width: 400,
      'ext-cls': 'redis-manage-infobox',
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: ticketType,
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
  };

  /**
   * 域名指向 clb / 域名解绑 clb
   */
  const handleSwitchDNSBindCLB = (data: RedisModel) => {
    const isBind = data.dns_to_clb;
    const title = isBind ? t('确认恢复 DNS 域名指向？') : t('确认将 DNS 域名指向 CLB ?');
    const subTitle = isBind ? t('DNS 域名恢复指向 Proxy') : t('业务不需要更换原域名也可实现负载均衡');
    const type = isBind ? TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB : TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB;
    InfoBox({
      title,
      subTitle,
      width: 400,
      'ext-cls': 'redis-manage-infobox',
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
  };

  /**
   * 集群 北极星启用/禁用
   */
  const handleSwitchPolaris = (data: RedisModel) => {
    const ticketType = data.isOnlinePolaris
      ? TicketTypes.REDIS_PLUGIN_DELETE_POLARIS
      : TicketTypes.REDIS_PLUGIN_CREATE_POLARIS;

    const title = ticketType === TicketTypes.REDIS_PLUGIN_CREATE_POLARIS ? t('确定启用北极星') : t('确定禁用北极星');
    useInfoWithIcon({
      type: 'warnning',
      title,
      onConfirm: async () => {
        try {
          const params = {
            bk_biz_id: globalBizsStore.currentBizId,
            ticket_type: ticketType,
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
  };

  /**
   * 删除集群
   */
  const handleDeleteCluster = (data: RedisModel) => {
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
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .redis-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;

    .operation-box {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }

      .cluster-dropdown {
        margin-right: auto;

        .cluster-dropdown-icon {
          color: @gray-color;
          transform: rotate(0);
          transition: all 0.2s;
        }

        .cluster-dropdown-icon-active {
          transform: rotate(-90deg);
        }
      }
    }

    .table-wrapper-out {
      flex: 1;
      overflow: hidden;

      .table-wrapper {
        background-color: white;

        .bk-table {
          height: 100% !important;
        }

        :deep(.cell) {
          line-height: unset !important;

          .db-icon-copy {
            display: none;
            margin-left: 4px;
            color: @primary-color;
            cursor: pointer;
          }
        }

        :deep(.cluster-name-container) {
          display: flex;
          align-items: flex-start;
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
            align-items: center;
            flex-wrap: wrap;
            margin-left: 4px;
          }

          .cluster-tag {
            flex-shrink: 0;
            margin: 2px;
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

        :deep(.bk-table-body) {
          max-height: calc(100% - 100px);
        }
      }
    }
  }
</style>

<style lang="less">
  .redis-manage-clb-minitag {
    color: #8e3aff;
    cursor: pointer;
    background-color: #f2edff;

    &:hover {
      color: #8e3aff;
      background-color: #e3d9fe;
    }
  }

  .redis-manage-polary-minitag {
    color: #3a84ff;
    cursor: pointer;
    background-color: #edf4ff;

    &:hover {
      color: #3a84ff;
      background-color: #e1ecff;
    }
  }

  .redis-manage-infobox {
    .bk-modal-body {
      .bk-modal-header {
        .bk-dialog-header {
          .bk-dialog-title {
            margin-top: 18px;
            margin-bottom: 16px;
          }
        }
      }

      .bk-modal-footer {
        height: 80px;
      }
    }
  }
</style>
