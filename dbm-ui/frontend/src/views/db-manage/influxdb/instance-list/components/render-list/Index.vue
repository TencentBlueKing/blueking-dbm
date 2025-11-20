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
  <div class="influxdb-instances-list">
    <div class="instances-view-header">
      <DbIcon
        v-if="curGroupInfo?.id"
        class="instances-view-header-icon mr-6"
        type="folder-open" />
      <DbIcon
        v-else
        class="instances-view-header-icon mr-6"
        type="summation" />
      <strong>{{ curGroupInfo?.name || t('全部实例') }}</strong>
    </div>
    <div class="instances-view-operations">
      <AuthButton
        action-id="influxdb_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <span
        v-bk-tooltips="{ content: t('请选择实例'), disabled: hasSelectedInstances }"
        class="ml-8">
        <BkButton
          :disabled="!hasSelectedInstances"
          @click="handleBatchRestart">
          {{ t('重启') }}
        </BkButton>
      </span>
      <BkDropdown
        :disabled="!hasSelectedInstances"
        @hide="() => (isShowGroupMove = false)"
        @show="() => (isShowGroupMove = true)">
        <span
          v-bk-tooltips="{ content: t('请选择实例'), disabled: hasSelectedInstances }"
          class="ml-8">
          <BkButton
            class="dropdown-button"
            :class="{ active: isShowGroupMove }"
            :disabled="!hasSelectedInstances">
            {{ t('移动至') }}
            <DbIcon type="up-big dropdown-button-icon" />
          </BkButton>
        </span>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem
              v-for="item in groupList"
              :key="item.id"
              :class="{
                'is-disabled':
                  item.id === groupId || (selectedGroupIds.length === 1 && selectedGroupIds.includes(item.id)),
              }"
              @click="handleGroupMove(item)">
              {{ item.name }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkDropdown
        @hide="() => (isCopyDropdown = false)"
        @show="() => (isCopyDropdown = true)">
        <BkButton
          class="dropdown-button ml-8"
          :class="{ active: isCopyDropdown }">
          {{ t('复制IP') }}
          <DbIcon type="up-big dropdown-button-icon" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopyAll()">
              {{ t('复制所有实例') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopy()">
              {{ t('复制已选实例') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAll(true)">
              {{ t('复制所有IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopy(true)">
              {{ t('复制已选IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DropdownExportExcel
        export-type="instance"
        :ids="selectedIds"
        type="influxdb" />
      <div class="instances-view-operations-right">
        <DbSearchSelect
          :data="searchSelectData"
          :get-menu-list="getMenuList"
          :model-value="searchValue"
          :placeholder="t('请输入或选择条件搜索')"
          :validate-values="validateSearchValues"
          @change="handleSearchValueChange" />
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :clear-selection="false"
      :columns="columns"
      :data-source="getInfluxdbInstanceList"
      :row-class="setRowClass"
      :settings="renderSettings"
      show-settings
      style="margin-bottom: 34px"
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @select="handleSelect"
      @select-all="handleSelectAll"
      @setting-change="updateTableSettings" />
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import _ from 'lodash';
  import type { Emitter } from 'mitt';
  import { useI18n } from 'vue-i18n';

  import InfluxDBInstanceModel from '@services/model/influxdb/influxdbInstance';
  import { getInfluxdbInstanceList } from '@services/source/influxdb';
  import { getGroupList, moveInstancesToGroup } from '@services/source/influxdbGroup';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach, useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderInstanceStatus from '@views/db-manage/common/RenderInstanceStatus.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import {
    execCopy,
    getMenuListSearch,
    getSearchSelectorParams,
    isRecentDays,
    messageSuccess,
    messageWarn,
  } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  type InfluxDBGroupItem = ServiceReturnType<typeof getGroupList>['results'][number];

  const route = useRoute();
  const router = useRouter();
  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const { locale, t } = useI18n();

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
    attrs: ['bk_cloud_id'],
    fetchDataFn: () => fetchTableData(),
    isCluster: false,
    searchType: ClusterTypes.INFLUXDB,
  });

  const eventBus = inject('eventBus') as Emitter<any>;

  const searchSelectData = computed(() => {
    const basicSelect = [
      {
        id: 'instance',
        name: t('IP 或 IP:Port'),
      },
      {
        id: 'id',
        name: 'ID',
      },
      {
        id: 'port',
        name: t('端口'),
      },
      {
        children: [
          { id: 'running', name: t('正常') },
          { id: 'unavailable', name: t('异常') },
        ],
        id: 'status',
        multiple: true,
        name: t('状态'),
      },
      {
        id: 'creator',
        name: t('创建人'),
      },
      {
        children: searchAttrs.value.bk_cloud_id,
        id: 'bk_cloud_id',
        multiple: true,
        name: t('管控区域'),
      },
    ];
    if (groupId.value === 0) {
      basicSelect.splice(2, 0, {
        children: groupList.value.map((item) => ({
          id: `${item.id}`,
          name: item.name,
        })),
        id: 'group_id',
        multiple: true,
        name: t('所属分组'),
      });
    }
    return basicSelect;
  });

  const isCN = computed(() => locale.value === 'zh-cn');
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isInit = ref(true);
  const isShowGroupMove = ref(false);
  const isCopyDropdown = ref(false);
  const groupList = shallowRef<InfluxDBGroupItem[]>([]);
  const batchSelectInstances = shallowRef<Record<number, InfluxDBInstanceModel>>({});
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});

  const selectedGroupIds = computed(() =>
    _.uniq(Object.values(batchSelectInstances.value).map((item) => item.group_id)),
  );
  const groupId = computed(() => {
    const groupId = route.params.groupId ?? 0;
    return Number(groupId);
  });
  const curGroupInfo = computed(() => groupList.value.find((item) => item.id === groupId.value));
  const hasSelectedInstances = computed(() => Object.keys(batchSelectInstances.value).length > 0);
  const selectedIds = computed(() => Object.values(batchSelectInstances.value).map((item) => item.bk_host_id));
  const renderSettings = computed(() => {
    const cloneSettings = _.cloneDeep(settings.value);
    if (groupId.value) {
      cloneSettings.fields = (cloneSettings?.fields || []).filter((item) => item.field !== 'group_name');
    }
    return cloneSettings;
  });

  const columns = computed(() => {
    const basicColumns = [
      {
        fixed: 'left',
        label: '',
        type: 'selection',
        width: 54,
      },
      {
        field: 'id',
        fixed: 'left',
        label: 'ID',
        width: 80,
      },
      {
        field: 'instance',
        fixed: 'left',
        label: t('实例'),
        minWidth: 300,
        render: ({ data }: { data: InfluxDBInstanceModel }) => (
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
                  {!data.isOnline && !data.isStarting && (
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
                  <db-icon
                    v-bk-tooltips={t('复制实例')}
                    class='mt-4'
                    type='copy'
                    onClick={() => copy([data.instance_address])}
                  />
                </>
              ),
              default: () => (
                <auth-router-link
                  to={{
                    name: 'InfluxDBInstDetails',
                    params: {
                      instId: data.id,
                    },
                    query: {
                      from: route.name as string,
                    },
                  }}
                  action-id='influxdb_view'
                  permission={data.permission.influxdb_view}
                  resource={data.id}>
                  {data.instance_address}
                </auth-router-link>
              ),
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'bk_cloud_id',
        filter: {
          checked: columnCheckedMap.value.bk_cloud_id,
          list: columnAttrs.value.bk_cloud_id,
        },
        label: t('管控区域'),
        render: ({ data }: { data: InfluxDBInstanceModel }) => <span>{data.bk_cloud_name ?? '--'}</span>,
      },
      {
        field: 'status',
        filter: {
          checked: columnCheckedMap.value.status,
          list: [
            {
              text: t('正常'),
              value: 'running',
            },
            {
              text: t('异常'),
              value: 'unavailable',
            },
          ],
        },
        label: t('状态'),
        minWidth: 100,
        render: ({ data }: { data: InfluxDBInstanceModel }) => <RenderInstanceStatus data={data.status} />,
      },
      {
        field: 'creator',
        label: t('创建人'),
        width: 100,
      },
      {
        field: 'create_at',
        label: t('部署时间'),
        render: ({ data }: { data: InfluxDBInstanceModel }) => <span>{data.createAtDisplay}</span>,
        sort: true,
        width: 200,
      },
      {
        field: '',
        fixed: 'right',
        label: t('操作'),
        render: ({ data }: { data: InfluxDBInstanceModel }) => {
          if (data.isOnline) {
            return (
              <>
                <OperationBtnStatusTips data={data}>
                  <auth-button
                    action-id='influxdb_reboot'
                    class='mr-8'
                    disabled={data.operationDisabled}
                    loading={tableDataActionLoadingMap.value[data?.id]}
                    permission={data.permission.influxdb_reboot}
                    resource={data.id}
                    theme='primary'
                    text
                    onClick={() => handleRestart([data])}>
                    {t('重启')}
                  </auth-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={data}>
                  <auth-button
                    action-id='influxdb_enable_disable'
                    class='mr-8'
                    disabled={data.operationDisabled}
                    loading={tableDataActionLoadingMap.value[data?.id]}
                    permission={data.permission.influxdb_enable_disable}
                    resource={data.id}
                    theme='primary'
                    text
                    onClick={() => handlDisabled(data)}>
                    {t('禁用')}
                  </auth-button>
                </OperationBtnStatusTips>
              </>
            );
          }
          return (
            <>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id='influxdb_enable_disable'
                  class='mr-8'
                  disabled={data.isStarting}
                  loading={tableDataActionLoadingMap.value[data?.id]}
                  permission={data.permission.influxdb_enable_disable}
                  resource={data.id}
                  theme='primary'
                  text
                  onClick={() => handleEnable(data)}>
                  {t('启用')}
                </auth-button>
              </OperationBtnStatusTips>
              <OperationBtnStatusTips data={data}>
                <auth-button
                  action-id='influxdb_destroy'
                  class='mr-8'
                  disabled={Boolean(data.operationTicketId)}
                  loading={tableDataActionLoadingMap.value[data?.id]}
                  permission={data.permission.influxdb_destroy}
                  resource={data.id}
                  theme='primary'
                  text
                  onClick={() => handlDelete(data)}>
                  {t('删除')}
                </auth-button>
              </OperationBtnStatusTips>
            </>
          );
        },
        width: isCN.value ? 140 : 200,
      },
    ];

    if (groupId.value === 0) {
      basicColumns.splice(2, 0, {
        field: 'group_id',
        filter: {
          checked: columnCheckedMap.value.group_id,
          list: groupList.value.map((item) => ({
            text: item.name,
            value: `${item.id}`,
          })),
        },
        label: t('所属分组'),
        minWidth: 100,
        render: ({ data }: { data: InfluxDBInstanceModel }) => <span>{data.group_name}</span>,
      });
    }
    return basicColumns;
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: ['instance', 'group_id', 'bk_cloud_id', 'status', 'creator', 'create_at'],
    fields: (columns.value || [])
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['instance'].includes(item.field as string),
        field: item.field as string,
        label: item.label as string,
      })),
    showLineHeight: true,
    trigger: 'manual' as const,
  };
  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.INFLUXDB_TABLE_SETTINGS,
    defaultSettings,
  );

  // 设置行样式
  const setRowClass = (row: InfluxDBInstanceModel) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    return classList.filter((cls) => cls).join(' ');
  };

  const formatInstanceData = (data: Array<InfluxDBInstanceModel>) =>
    data.map((item) => {
      const [ip, port] = item.instance_address.split(':');
      return {
        bk_cloud_id: item.bk_cloud_id,
        bk_host_id: item.bk_host_id,
        instance_id: item.id,
        instance_name: item.instance_name,
        ip,
        port: Number(port),
      };
    });

  const fetchTableData = (loading?: boolean) => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(
      searchParams,
      {
        group_id: groupId.value === 0 ? (searchParams.group_id ? searchParams.group_id : undefined) : groupId.value,
        ...sortValue,
      },
      loading,
    );
    isInit.value = false;
  };

  const { resume: resumeFetchTableData } = useTimeoutPoll(() => fetchTableData(isInit.value), 30000, {
    immediate: false,
  });

  watch(
    () => route.params.groupId,
    () => {
      tableRef.value?.updateTableKey();
      fetchTableData();
    },
  );

  onMounted(() => {
    resumeFetchTableData();
  });

  watch(searchValue, () => {
    tableRef.value!.clearSelected();
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

  const updateGroupList = (list: InfluxDBGroupItem[] = []) => {
    groupList.value = list;
  };

  const handleCopyAll = (isIp = false) => {
    tableRef.value!.getAllData<InfluxDBInstanceModel>().then((influxdbList) => {
      const list = influxdbList.map((item) => item.instance_address);
      if (isIp) {
        copy(list.map((inst) => inst.split(':')[0]));
        return;
      }
      copy(list);
    });
  };

  const handleCopy = (isIp = false) => {
    const list = Object.values(batchSelectInstances.value).map((item) => item.instance_address);
    if (list.length === 0) {
      messageWarn(t('请选择实例'));
      return;
    }

    if (isIp) {
      copy(list.map((inst) => inst.split(':')[0]));
      return;
    }

    copy(list);
  };

  const copy = (list: string[]) => {
    execCopy(list.join(','), t('复制成功，共n条', { n: list.length }));
  };

  // 选择单台
  const handleSelect = (data: { checked: boolean; row: InfluxDBInstanceModel }) => {
    const selectedMap = { ...batchSelectInstances.value };
    if (data.checked) {
      selectedMap[data.row.id] = data.row;
    } else {
      delete selectedMap[data.row.id];
    }

    batchSelectInstances.value = selectedMap;
  };

  // 选择所有
  const handleSelectAll = (data: { checked: boolean }) => {
    let selectedMap = { ...batchSelectInstances.value };
    if (data.checked) {
      selectedMap = (tableRef.value!.getData() as InfluxDBInstanceModel[]).reduce(
        (result, item) => ({
          ...result,
          [item.id]: item,
        }),
        {},
      );
    } else {
      selectedMap = {};
    }
    batchSelectInstances.value = selectedMap;
  };

  /**
   * 操作 loading 状态
   */
  const handleChangeTableActionLoading = (id: number, isLoading = false) => {
    tableDataActionLoadingMap.value = {
      ...tableDataActionLoadingMap.value,
      [id]: isLoading,
    };
  };

  /**
   * 移动实例分组
   */
  const handleGroupMove = (data: InfluxDBGroupItem) => {
    if (data.id === groupId.value || (selectedGroupIds.value.length === 1 && selectedGroupIds.value.includes(data.id)))
      return;
    moveInstancesToGroup({
      instance_ids: Object.values(batchSelectInstances.value).map((item) => item.id),
      new_group_id: data.id,
    }).then(() => {
      messageSuccess(t('移动分组成功'));
      fetchTableData();
      batchSelectInstances.value = {};
      eventBus.emit('fetch-group-list');
      tableRef.value!.clearSelected();
    });
  };

  const handleBatchRestart = () => {
    handleRestart(Object.values(batchSelectInstances.value));
  };

  /**
   * 重启实例
   */
  const handleRestart = (data: InfluxDBInstanceModel[]) => {
    InfoBox({
      confirmText: t('重启'),
      content: () => (
        <div style='word-break: all;'>
          <p>{t('以下实例重启连接将会断开_请谨慎操作')}</p>
          {data.map((item) => (
            <p>{item.instance_address}</p>
          ))}
        </div>
      ),
      onConfirm: () => {
        data.forEach((item) => {
          handleChangeTableActionLoading(item.id, true);
        });
        return createTicket({
          bk_biz_id: currentBizId,
          details: {
            instance_list: formatInstanceData(data),
          },
          ticket_type: 'INFLUXDB_REBOOT',
        })
          .then((res) => {
            ticketMessage(res.id);
            if (data.length > 1) {
              tableRef.value!.clearSelected();
            }
          })
          .finally(() => {
            data.forEach((item) => {
              handleChangeTableActionLoading(item.id, false);
            });
          });
      },
      title: t('确认重启实例'),
      type: 'warning',
      width: 480,
    });
  };

  /**
   * 启用实例
   */
  const handleEnable = (data: InfluxDBInstanceModel) => {
    InfoBox({
      confirmText: t('启用'),
      content: () => (
        <div style='word-break: all;'>
          <p>{t('实例【instance】启用后将恢复访问', { instance: data.instance_address })}</p>
        </div>
      ),
      onConfirm: () => {
        handleChangeTableActionLoading(data.id, true);
        return createTicket({
          bk_biz_id: currentBizId,
          details: {
            instance_list: formatInstanceData([data]),
          },
          ticket_type: 'INFLUXDB_ENABLE',
        })
          .then((res) => {
            ticketMessage(res.id);
          })
          .finally(() => {
            handleChangeTableActionLoading(data.id, false);
          });
      },
      title: t('确认启用该实例'),
      type: 'warning',
      width: 480,
    });
  };

  /**
   * 禁用实例
   */
  const handlDisabled = (data: InfluxDBInstanceModel) => {
    InfoBox({
      confirmText: t('禁用'),
      content: () => (
        <div style='word-break: all;'>
          <p>
            {t('实例【instance】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { instance: data.instance_address })}
          </p>
        </div>
      ),
      onConfirm: () => {
        handleChangeTableActionLoading(data.id, true);
        return createTicket({
          bk_biz_id: currentBizId,
          details: {
            instance_list: formatInstanceData([data]),
          },
          ticket_type: 'INFLUXDB_DISABLE',
        })
          .then((res) => {
            ticketMessage(res.id);
          })
          .finally(() => {
            handleChangeTableActionLoading(data.id, false);
          });
      },
      title: t('确认禁用该实例'),
      type: 'warning',
      width: 480,
    });
  };

  /**
   * 下架实例
   */
  const handlDelete = (data: InfluxDBInstanceModel) => {
    const instanceAddress = data.instance_address;
    InfoBox({
      confirmButtonTheme: 'danger',
      confirmText: t('删除'),
      content: () => (
        <div style='word-break: all; text-align: left; padding-left: 16px;'>
          <p>{t('实例【instance】被删除后_将进行以下操作', { instance: instanceAddress })}</p>
          <p>{t('1_删除xx实例', { instance: instanceAddress })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name: instanceAddress })}</p>
        </div>
      ),
      onConfirm: () => {
        handleChangeTableActionLoading(data.id, true);
        return createTicket({
          bk_biz_id: currentBizId,
          details: {
            instance_list: formatInstanceData([data]),
          },
          ticket_type: 'INFLUXDB_DESTROY',
        })
          .then((res) => {
            ticketMessage(res.id);
          })
          .finally(() => {
            handleChangeTableActionLoading(data.id, false);
          });
      },
      title: t('确定删除该实例'),
      type: 'warning',
      width: 480,
    });
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyInfluxDB',
      query: {
        bizId: currentBizId,
        from: route.name as string,
        groupId: groupId.value,
      },
    });
  };

  eventBus.on('update-group-list', updateGroupList);

  onBeforeUnmount(() => {
    eventBus.off('update-group-list', updateGroupList);
  });
</script>

<style lang="less">
  .influxdb-instances-list {
    height: 100%;
    padding: 24px;
    background-color: white;

    tr {
      &:hover {
        .db-icon-copy {
          display: inline-block;
        }
      }
    }

    .instances-view-header {
      display: flex;
      height: 20px;
      color: @title-color;
      align-items: center;

      .instances-view-header-icon {
        font-size: 18px;
        color: @gray-color;
      }
    }

    .instances-view-operations {
      display: flex;
      align-items: center;
      padding: 16px 0;

      .instances-view-operations-right {
        flex: 1;
        display: flex;
        justify-content: flex-end;
      }

      .dropdown-button {
        .dropdown-button-icon {
          margin-left: 6px;
          transition: all 0.2s;
        }

        &.active:not(.is-disabled) {
          .dropdown-button-icon {
            transform: rotate(180deg);
          }
        }
      }
    }

    .instance-box {
      display: flex;
      align-items: flex-start;
      padding: 8px 0;
      overflow: hidden;

      .instance-name {
        line-height: 20px;
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

      .db-icon-copy {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    .is-offline {
      a {
        color: @gray-color;
      }

      .vxe-cell {
        color: @disable-color;
      }
    }
  }

  .bk-dropdown-item {
    &.is-disabled {
      color: @disable-color;
      cursor: not-allowed;
    }
  }
</style>
