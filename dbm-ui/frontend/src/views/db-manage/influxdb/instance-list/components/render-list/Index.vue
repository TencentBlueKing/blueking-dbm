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
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click"
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
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click"
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
        <DbQuickSearch
          v-model="searchValue"
          :data="searchSelectData"
          parse-url
          :placeholder="t('请输入或选择条件搜索')"
          @change="handleSearchValueChange" />
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :bk-ui-settings="settings"
      :data-source="getInfluxdbInstanceList"
      :filter-value="searchValue"
      :row-class-name="setRowClass"
      row-key="id"
      selectable
      style="margin-bottom: 34px"
      @bk-ui-settings-change="updateTableSettings"
      @clear-search="clearSearchValue"
      @filter-change="handleFilterChange"
      @selection="handleSelection"
      @sort-change="handleSortChange">
      <TableColumn
        col-key="id"
        fixed="left"
        title="ID"
        :width="80">
      </TableColumn>
      <TableColumn
        v-if="groupId === 0"
        col-key="group_id"
        :filter="{
          list: groupFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :min-width="100"
        :title="t('所属分组')">
        <template #default="{ row: data }: { row: InfluxDBInstanceModel }">
          <span>{{ data.group_name }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="instance"
        :ellipsis="false"
        fixed="left"
        :min-width="300"
        :title="t('实例')">
        <template #default="{ row: data }: { row: InfluxDBInstanceModel }">
          <TextOverflowLayout>
            <AuthRouterLink
              action-id="influxdb_view"
              :permission="data.permission.influxdb_view"
              :resource="data.id"
              :to="{
                name: 'InfluxDBInstDetails',
                params: {
                  instId: data.id,
                },
                query: {
                  from: route.name as string,
                },
              }">
              {{ data.instance_address }}
            </AuthRouterLink>
            <template #append>
              <RenderOperationTag
                v-for="(item, index) in data.operationTagTips"
                :key="index"
                class="cluster-tag ml-4"
                :data="item" />
              <BkTag
                v-if="!data.isOnline && !data.isStarting"
                class="ml-4"
                size="small">
                {{ t('已禁用') }}
              </BkTag>
              <BkTag
                v-if="data.isNew"
                class="ml-4"
                size="small"
                theme="success">
                NEW
              </BkTag>
              <DbIcon
                v-bk-tooltips="t('复制实例')"
                class="mt-4"
                type="copy"
                @click="copy([data.instance_address])" />
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_cloud_id"
        :filter="{
          list: cloudFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :title="t('管控区域')">
        <template #default="{ row: data }: { row: InfluxDBInstanceModel }">
          <span>{{ data.bk_cloud_name ?? '--' }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="{
          list: statusFilterList,
          showConfirmAndReset: true,
          type: 'multiple',
        }"
        :min-width="100"
        :title="t('状态')">
        <template #default="{ row: data }: { row: InfluxDBInstanceModel }">
          <RenderInstanceStatus :data="data.status" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="creator"
        :title="t('创建人')"
        :width="100">
      </TableColumn>
      <TableColumn
        col-key="create_at"
        sorter
        :title="t('部署时间')"
        :width="200">
        <template #default="{ row: data }: { row: InfluxDBInstanceModel }">
          <span>{{ data.createAtDisplay }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="isCN ? 140 : 200">
        <template #default="{ row: data }: { row: InfluxDBInstanceModel }">
          <template v-if="data.isOnline">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="influxdb_reboot"
                class="mr-8"
                :disabled="data.operationDisabled"
                :loading="tableDataActionLoadingMap[data.id]"
                :permission="data.permission.influxdb_reboot"
                :resource="data.id"
                text
                theme="primary"
                @click="handleRestart([data])">
                {{ t('重启') }}
              </AuthButton>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="influxdb_enable_disable"
                class="mr-8"
                :disabled="data.operationDisabled"
                :loading="tableDataActionLoadingMap[data.id]"
                :permission="data.permission.influxdb_enable_disable"
                :resource="data.id"
                text
                theme="primary"
                @click="handlDisabled(data)">
                {{ t('禁用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </template>
          <template v-else>
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="influxdb_enable_disable"
                class="mr-8"
                :disabled="data.isStarting"
                :loading="tableDataActionLoadingMap[data.id]"
                :permission="data.permission.influxdb_enable_disable"
                :resource="data.id"
                text
                theme="primary"
                @click="handleEnable(data)">
                {{ t('启用') }}
              </AuthButton>
            </OperationBtnStatusTips>
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="influxdb_destroy"
                class="mr-8"
                :disabled="Boolean(data.operationTicketId)"
                :loading="tableDataActionLoadingMap[data.id]"
                :permission="data.permission.influxdb_destroy"
                :resource="data.id"
                text
                theme="primary"
                @click="handlDelete(data)">
                {{ t('删除') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </template>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import type { Emitter } from 'mitt';
  import type { TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import InfluxDBInstanceModel from '@services/model/influxdb/influxdbInstance';
  import { queryBizClusterAttrs } from '@services/source/dbbase';
  import { getInfluxdbInstanceList } from '@services/source/influxdb';
  import { getGroupList, moveInstancesToGroup } from '@services/source/influxdbGroup';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import { useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';
  import { ipPort, ipv4 } from '@common/regex';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderInstanceStatus from '@views/db-manage/common/RenderInstanceStatus.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { execCopy, isRecentDays, messageSuccess, messageWarn, transfromDataToQuery } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  type InfluxDBGroupItem = ServiceReturnType<typeof getGroupList>['results'][number];

  const route = useRoute();
  const router = useRouter();
  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const { locale, t } = useI18n();

  const searchValue = ref<Record<string, string>>({});
  const sortValue: {
    ordering?: string;
  } = {};
  const cloudAttrsList = shallowRef<{ label: string; value: string }[]>([]);

  queryBizClusterAttrs({
    bk_biz_id: currentBizId,
    cluster_type: ClusterTypes.INFLUXDB,
    instances_attrs: 'bk_cloud_id',
  }).then((data) => {
    cloudAttrsList.value = data.bk_cloud_id.map((item) => ({
      label: item.text,
      value: item.value,
    }));
  });

  const eventBus = inject('eventBus') as Emitter<any>;

  const searchSelectData = computed(() => {
    const basicSelect = [
      {
        id: 'instance',
        name: t('IP 或 IP:Port'),
        type: 'multiple-input',
        validator: (value: string) => ipPort.test(value) || ipv4.test(value) || t('格式错误'),
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
        id: 'status',
        list: [
          { label: t('正常'), value: 'running' },
          { label: t('异常'), value: 'unavailable' },
        ],
        name: t('状态'),
        type: 'multiple',
      },
      {
        id: 'creator',
        name: t('创建人'),
        remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
          const requestParams = {};
          if (params.defaultValue) {
            Object.assign(requestParams, { exact_lookups: params.defaultValue });
          }
          if (params.keyword) {
            Object.assign(requestParams, { fuzzy_lookups: params.keyword });
          }

          return getUserList(requestParams).then((data) =>
            data.results.map((item) => ({
              label: item.username,
              value: item.username,
            })),
          );
        },
        remoteSearch: true,
        type: 'multiple',
      },
      {
        id: 'bk_cloud_id',
        list: cloudAttrsList.value,
        name: t('管控区域'),
        type: 'multiple',
      },
    ] as QuickSearchProps['data'];
    if (groupId.value === 0) {
      basicSelect.splice(2, 0, {
        id: 'group_id',
        list: groupList.value.map((item) => ({
          label: item.name,
          value: `${item.id}`,
        })),
        name: t('所属分组'),
        type: 'multiple',
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

  const statusFilterList = [
    {
      label: t('正常'),
      value: 'running',
    },
    {
      label: t('异常'),
      value: 'unavailable',
    },
  ];
  const cloudFilterList = computed(() => cloudAttrsList.value);
  const groupFilterList = computed(() =>
    groupList.value.map((item) => ({
      label: item.name,
      value: `${item.id}`,
    })),
  );

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: ['instance', 'group_id', 'bk_cloud_id', 'status', 'creator', 'create_at'],
    disabled: ['instance'],
  };
  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.INFLUXDB_TABLE_SETTINGS,
    defaultSettings,
  );

  // 设置行样式
  const setRowClass = ({ row }: { row: InfluxDBInstanceModel }) => {
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
    const searchParams: Record<string, string> = transfromDataToQuery(searchValue.value);
    tableRef.value?.fetchData(
      {
        ...searchParams,
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
    fetchTableData();
    resumeFetchTableData();
  });

  const handleSearchValueChange = () => {
    fetchTableData();
  };

  const clearSearchValue = () => {
    searchValue.value = {};
    fetchTableData();
  };

  const updateGroupList = (list: InfluxDBGroupItem[] = []) => {
    groupList.value = list;
  };

  const handleCopyAll = (isIp = false) => {
    tableRef.value!.fetchAllData<InfluxDBInstanceModel>().then((influxdbList) => {
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

  // 选择变更
  const handleSelection = (_keys: string[], list: InfluxDBInstanceModel[]) => {
    batchSelectInstances.value = list.reduce<Record<number, InfluxDBInstanceModel>>(
      (result, item) => ({
        ...result,
        [item.id]: item,
      }),
      {},
    );
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
    fetchTableData();
  };

  const handleSortChange = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }
    if (payload) {
      sortValue.ordering = payload.descending ? `-${payload.sortBy}` : payload.sortBy;
    } else {
      delete sortValue.ordering;
    }
    fetchTableData();
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
              data.forEach((item) => tableRef.value?.removeSelectByKey(`${item.id}`));
              batchSelectInstances.value = {};
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
      name: TicketTypes.INFLUXDB_APPLY,
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

      td {
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
