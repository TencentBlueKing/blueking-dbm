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
  <div class="doris-list-page">
    <div class="header-action">
      <AuthButton
        action-id="es_apply"
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <BkDropdown
        class="ml-8"
        @hide="() => (isCopyDropdown = false)"
        @show="() => (isCopyDropdown = true)">
        <BkButton
          class="dropdown-button"
          :class="{ active: isCopyDropdown }">
          {{ t('复制') }}
          <DbIcon type="up-big dropdown-button-icon" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="tableDataList.length === 0"
                text
                @click="handleCopy(tableDataList)">
                {{ t('所有集群 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="selected.length === 0"
                text
                @click="handleCopy(selected)">
                {{ t('已选集群 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="abnormalDataList.length === 0"
                text
                @click="handleCopy(abnormalDataList)">
                {{ t('异常集群 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="tableDataList.length === 0"
                text
                @click="handleCopy(tableDataList, true)">
                {{ t('所有集群实例') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="selected.length === 0"
                text
                @click="handleCopy(selected, true)">
                {{ t('已选集群实例') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                :disabled="abnormalDataList.length === 0"
                text
                @click="handleCopy(abnormalDataList, true)">
                {{ t('异常集群实例') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DropdownExportExcel
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="doris" />
      <DbSearchSelect
        v-model="searchValues"
        class="mb16"
        :data="serachData"
        :placeholder="t('输入集群名_IP_访问入口关键字')"
        unique-select
        @change="handleSearch" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getDorisList"
        :pagination-extra="paginationExtra"
        releate-url-query
        :row-class="getRowClass"
        selectable
        :settings="tableSetting"
        @clear-search="handleClearSearch"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      :title="t('xx扩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="t('xx缩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="operationData"
        :node-list="[]"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      :title="t('获取访问方式')">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import {
    getDorisInstanceList,
    getDorisList,
  } from '@services/source/doris';
  import { createTicket } from '@services/source/ticket';

  import {
    useCopy,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes, UserPersonalSettings } from '@common/const';

  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderNodeInstance from '@components/cluster-common/RenderNodeInstance.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTagNew.vue';
  import RenderPassword from '@components/cluster-common/RenderPassword.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import DbTable from '@components/db-table/index.vue'
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterExpansion from '@views/doris-manage/common/expansion/Index.vue';
  import ClusterShrink from '@views/doris-manage/common/shrink/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const copy = useCopy();
  const {
    t,
    locale,
  } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const serachData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名'),
      id: 'name',
    },
    {
      name: t('访问入口'),
      id: 'domain',
    },
    {
      name: 'IP',
      id: 'ip',
    },
  ];

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isCopyDropdown = ref(false);
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isInit = ref(true);
  const searchValues = ref([]);

  const selected = shallowRef<DorisModel[]>([]);
  const operationData = shallowRef<DorisModel>();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});

  const tableDataList = computed(() => tableRef.value!.getData<DorisModel>());
  const abnormalDataList = computed(() => tableDataList.value.filter(dataItem => dataItem.isAbnormal));
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));

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
  const isCN = computed(() => locale.value === 'zh-cn');

  const getRowClass = (data: DorisModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = data.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 270 : 420;
    }
    return 100;
  });
  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('访问入口'),
      field: 'domain',
      width: 200,
      minWidth: 200,
      fixed: 'left',
      render: ({ data }: { data: DorisModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="es_view"
                resource={data.id}
                permission={data.permission.es_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.domainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                {
                  data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
                }
                {
                  !data.isOnline && !data.isStarting && (
                    <bk-tag
                      class="ml-4"
                      size="small">
                      {t('已禁用')}
                    </bk-tag>
                  )
                }
                {
                  data.isNew && (
                    <bk-tag
                      theme="success"
                      size="small"
                      class="ml-4">
                      NEW
                    </bk-tag>
                  )
                }
                {
                  data.domain && (
                    <db-icon
                      type="copy"
                      v-bk-tooltips={t('复制访问入口')}
                      onClick={() => copy(data.domainDisplayName)} />
                  )
                }
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      width: 150,
      minWidth: 150,
      fixed: 'left',
      showOverflowTooltip: false,
      render: ({ data }: { data: DorisModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <div>
                <span>
                  {data.cluster_name}
                </span >
                <div style='color: #C4C6CC;'>{data.cluster_alias || '--'}</div>
              </div>
            ),
            append: () => (
              <db-icon
                v-bk-tooltips={t('复制集群名称')}
                type="copy"
                class="mt-2"
                onClick={() => copy(data.cluster_name)} />
            )
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 100,
      render: ({ data }: { data: DorisModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      render: ({ data }: { data: DorisModel }) => <span>{data?.region || '--'}</span>,
    },
    {
      label: t('Follower节点'),
      field: 'doris_follower',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          role="doris_follower"
          title={`【${data.domain}】follower`}
          clusterId={data.id}
          originalList={data.doris_follower}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('Observer节点'),
      field: 'doris_observer',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          role="doris_observer"
          title={`【${data.domain}】observer`}
          clusterId={data.id}
          originalList={data.doris_observer}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('热节点'),
      field: 'doris_datanode_hot',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          role="doris_datanode_hot"
          title={t('【xx】热节点', { name: data.domain })}
          clusterId={data.id}
          originalList={data.doris_datanode_hot}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('冷节点'),
      field: 'doris_datanode_cold',
      minWidth: 230,
      showOverflowTooltip: false,
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          role="doris_datanode_cold"
          title={t('【xx】冷节点', { name: data.domain })}
          clusterId={data.id}
          originalList={data.doris_datanode_cold}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 160,
      render: ({ data }: { data: DorisModel }) => <span>{data.createAtDisplay}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: { data: DorisModel }) => {
        if (data.isOnline) {
          return [
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                theme="primary"
                class="mr-16"
                action-id="es_scale_up"
                permission={data.permission.es_scale_up}
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowExpandsion(data)}>
                { t('扩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                theme="primary"
                class="mr-16"
                action-id="es_shrink"
                permission={data.permission.es_shrink}
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowShrink(data)}>
                { t('缩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <auth-button
              text
              theme="primary"
              action-id="es_view"
              permission={data.permission.es_view}
              resource={data.id}
              class="mr-16"
              onClick={() => handleShowPassword(data)}>
              {t('获取访问方式')}
            </auth-button>,
            <bk-dropdown>
              {{
                default: () => (
                  <bk-button text>
                    <db-icon type="more" />
                  </bk-button>
                ),
                content: () => (
                  <>
                    <bk-dropdown-item>
                      <a
                        href={data.access_url}
                        target="_blank">
                        {t('管理')}
                      </a>,
                    </bk-dropdown-item>
                    <bk-dropdown-item>
                      <OperationBtnStatusTips data={data}>
                        <auth-button
                          text
                          theme="primary"
                          action-id="es_enable_disable"
                          permission={data.permission.es_enable_disable}
                          resource={data.id}
                          disabled={data.operationDisabled}
                          loading={tableDataActionLoadingMap.value[data.id]}
                          onClick={() => handlDisabled(data)}>
                          { t('禁用') }
                        </auth-button>
                      </OperationBtnStatusTips>
                    </bk-dropdown-item>
                  </>
                )
              }}
            </bk-dropdown>
          ];
        }
        return [
          <auth-button
            text
            theme="primary"
            action-id="es_enable_disable"
            permission={data.permission.es_enable_disable}
            resource={data.id}
            class="mr-16"
            loading={tableDataActionLoadingMap.value[data.id]}
            onClick={() => handleEnable(data)}>
            { t('启用') }
          </auth-button>,
          <auth-button
            text
            theme="primary"
            action-id="es_destroy"
            permission={data.permission.es_destroy}
            resource={data.id}
            loading={tableDataActionLoadingMap.value[data.id]}
            onClick={() => handleRemove(data)}>
            { t('删除') }
          </auth-button>,
        ];
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: item.field === 'domain',
    })),
    checked: [
      'domain',
      'cluster_name',
      'bk_cloud_name',
      'major_version',
      'region',
      'status',
      'doris_follower',
      'doris_observer',
      'doris_datanode_hot',
      'doris_datanode_cold',
      'cluster_time_zone',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.DORIS_TABLE_SETTINGS, defaultSettings);

  const fetchTableData = (loading?:boolean) => {
    const searchParams = getSearchSelectorParams(searchValues.value);
    tableRef.value?.fetchData(searchParams, {}, loading);
    isInit.value = false;
  };

  const handleSelection = (key: number[], list: Record<number, DorisModel>[]) => {
    selected.value = list as unknown as DorisModel[];
  };

  const {
    resume: resumeFetchTableData,
  } = useTimeoutPoll(() => fetchTableData(isInit.value), 5000, {
    immediate: false,
  });

  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'DorisApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleCopy = (dataList: DorisModel[], isInstance = false) => {
    const list = dataList.reduce((prevList, tableItem) => {
      const followerList = tableItem.doris_follower.map(followerItem => (isInstance ? `${followerItem.ip}:${followerItem.port}` : `${followerItem.ip}`));
      const observerList = tableItem.doris_observer.map(observerItem => (isInstance ? `${observerItem.ip}:${observerItem.port}` : `${observerItem.ip}`));
      const hotList = tableItem.doris_datanode_hot.map(hotItem => (isInstance ? `${hotItem.ip}:${hotItem.port}` : `${hotItem.ip}`));
      const coldList = tableItem.doris_datanode_cold.map(coldItem => (isInstance ? `${coldItem.ip}:${coldItem.port}` : `${coldItem.ip}`));
      return [...followerList, ...observerList, ...hotList, ...coldList];
    }, [] as string[]);
    copy(list.join('\n'));
  };

  // 搜索
  const handleSearch = () => {
    fetchTableData();
  };

  // 清空搜索
  const handleClearSearch = () => {
    searchValues.value = [];
    fetchTableData();
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 扩容
  const handleShowExpandsion = (data: DorisModel) => {
    isShowExpandsion.value = true;
    operationData.value = data;
  };

  // 缩容
  const handleShowShrink = (data: DorisModel) => {
    isShowShrink.value = true;
    operationData.value = data;
  };

  // 禁用
  const handlDisabled =  (clusterData: DorisModel) => {
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div>
          {t('集群')} :
          <span
            style="color: #313238"
            class="ml-8">
            {clusterData.cluster_name}
          </span>
        </div>
        <div class='mt-4'>{t('被禁用后将无法访问，如需恢复访问，可以再次「启用」')}</div>
      </div>
    )
    InfoBox({
      title: t('确认禁用该集群？'),
      subTitle,
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('禁用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.DORIS_DISABLE,
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleEnable =  (clusterData: DorisModel) => {
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div>
          {t('集群')} :
          <span
            style="color: #313238"
            class="ml-8">
            {clusterData.cluster_name}
          </span>
        </div>
        <div class='mt-4'>{t('启用后，将会恢复访问')}</div>
      </div>
    )
    InfoBox({
      title: t('确认启用该集群？'),
      subTitle,
      confirmText: t('启用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.ES_ENABLE,
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleRemove =  (clusterData: DorisModel) => {
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div>
          {t('集群')} :
          <span
            style="color: #313238"
            class="ml-8">
            {clusterData.cluster_name}
          </span>
        </div>
        <div class='mt-4'>{t('删除后将产生以下影响')}：</div>
        <div class='mt-4'>1. {t('删除xxx集群', [clusterData.cluster_name])}</div>
        <div class='mt-4'>2. {t('删除xxx实例数据，停止相关进程', [clusterData.cluster_name])}</div>
        <div class='mt-4'>3. {t('回收主机')}：</div>
      </div>
    )
    InfoBox({
      title: t('确认删除【name】集群', { name: clusterData.cluster_name }),
      subTitle,
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('删除'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.ES_DESTROY,
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleShowPassword = (clusterData: DorisModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  onMounted(() => {
    resumeFetchTableData();
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less">
  .doris-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;

      .db-table,
      .audit-render-list,
      .bk-nested-loading {
        height: 100%;
      }

      .bk-table {
        height: 100% !important;
      }

      .bk-table-body {
        max-height: calc(100% - 100px);
      }
    }

    .is-shrink-table {
      .bk-table-body {
        overflow: hidden auto;
      }
    }

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

    .is-offline {
      * {
        color: #c4c6cc !important;
      }

      a,
      i,
      .bk-button.bk-button-primary .bk-button-text {
        color: #3a84ff !important;
      }
    }

    .db-icon-copy {
      display: none;
    }

    tr:hover {
      .db-icon-copy {
        display: inline-block !important;
        margin-left: 4px;
        color: #3a84ff;
        vertical-align: middle;
        cursor: pointer;
      }
    }
  }
</style>

<style lang="less" scoped>
  .doris-list-page {
    :deep(.cell) {
      line-height: normal !important;

      .db-icon-edit {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(tr:hover) {
      .db-icon-edit {
        display: inline-block !important;
      }
    }
  }
</style>
