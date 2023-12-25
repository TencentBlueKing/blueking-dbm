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
      <strong>{{ curGroupInfo?.name || $t('全部实例') }}</strong>
    </div>
    <div class="instances-view-operations">
      <BkButton
        theme="primary"
        @click="handleApply">
        {{ $t('实例申请') }}
      </BkButton>
      <span
        v-bk-tooltips="{content: $t('请选择实例'), disabled: hasSelectedInstances }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelectedInstances"
          @click="handleBatchRestart">
          {{ $t('重启') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{content: $t('请选择实例'), disabled: hasSelectedInstances }"
        class="inline-block">
        <BkButton
          :disabled="!hasSelectedInstances"
          @click="handleShowReplace()">
          {{ $t('替换') }}
        </BkButton>
      </span>
      <BkDropdown
        :disabled="!hasSelectedInstances"
        @hide="() => isShowGroupMove = false"
        @show="() => isShowGroupMove = true">
        <span
          v-bk-tooltips="{content: $t('请选择实例'), disabled: hasSelectedInstances }"
          class="inline-block">
          <BkButton
            class="dropdown-button"
            :class="{ 'active': isShowGroupMove }"
            :disabled="!hasSelectedInstances">
            {{ $t('移动至') }}
            <DbIcon type="up-big dropdown-button-icon" />
          </BkButton>
        </span>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem
              v-for="item in groupList"
              :key="item.id"
              :class="{
                'is-disabled': item.id === groupId
                  || (selectedGroupIds.length === 1 && selectedGroupIds.includes(item.id))
              }"
              @click="handleGroupMove(item)">
              {{ item.name }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkDropdown
        @hide="() => isCopyDropdown = false"
        @show="() => isCopyDropdown = true">
        <BkButton
          class="dropdown-button"
          :class="{ 'active': isCopyDropdown }">
          {{ $t('复制IP') }}
          <DbIcon type="up-big dropdown-button-icon" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopyAll()">
              {{ $t('复制全部实例') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopy()">
              {{ $t('复制已选实例') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAll(true)">
              {{ $t('复制全部IP') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopy(true)">
              {{ $t('复制已选IP') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DropdownExportExcel
        export-type="instance"
        type="influxdb" />
      <div class="instances-view-operations-right">
        <DbSearchSelect
          v-model="search"
          :data="searchSelectData"
          style="width: 500px;"
          @change="fetchTableData()" />
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :clear-selection="false"
      :columns="columns"
      :data-source="getInfluxdbInstanceList"
      :row-class="setRowClass"
      :settings="renderSettings"
      style="margin-bottom: 34px;"
      @clear-search="handleClearFilters"
      @select="handleSelect"
      @select-all="handleSelectAll"
      @setting-change="updateTableSettings" />
  </div>
  <DbSideslider
    v-model:is-show="isShowReplace"
    :disabled-confirm="operationNodeList.length === 0"
    :title="$t('InfluxDB实例替换')"
    :width="960">
    <ClusterReplace
      :node-list="operationNodeList"
      @remove-node="handleRemoveNodeSelect"
      @succeeded="handleReplaceSucceeded" />
  </DbSideslider>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { Emitter } from 'mitt';
  import { useI18n } from 'vue-i18n';

  import type InfluxDBInstanceModel from '@services/model/influxdb/influxdbInstance';
  import { getInfluxdbInstanceList } from '@services/source/influxdb';
  import { moveInstancesToGroup } from '@services/source/influxdbGroup';
  import { createTicket } from '@services/source/ticket';
  import type { InfluxDBGroupItem } from '@services/types/influxdbGroup';

  import { useCopy, useInfoWithIcon, useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import OperationStatusTips from '@components/cluster-common/OperationStatusTips.vue';
  import RenderInstanceStatus from '@components/cluster-common/RenderInstanceStatus.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTag.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
    messageSuccess,
    messageWarn,
  } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import ClusterReplace from './components/Replace.vue';

  const route = useRoute();
  const router = useRouter();
  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const { t, locale } = useI18n();
  const copy = useCopy();
  const eventBus = inject('eventBus') as Emitter<any>;

  const searchSelectData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('实例'),
      id: 'instance_address',
    },
    {
      name: 'IP',
      id: 'ip',
    },
    {
      name: t('端口'),
      id: 'port',
    },
    {
      name: t('状态'),
      id: 'status',
      children: [
        { id: 'running', name: t('正常') },
        { id: 'unavailable', name: t('异常') },
      ],
    },
  ];

  const isCN = computed(() => locale.value === 'zh-cn');
  const tableRef = ref();
  const isInit = ref(true);
  const isShowGroupMove = ref(false);
  const isCopyDropdown = ref(false);
  const isShowReplace = ref(false);
  const search = ref([]);
  const operationNodeList = shallowRef<Array<InfluxDBInstanceModel>>([]);
  const groupList = shallowRef<InfluxDBGroupItem[]>([]);
  const batchSelectInstances = shallowRef<Record<number, InfluxDBInstanceModel>>({});
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});


  const selectedGroupIds = computed(() => _.uniq(Object.values(batchSelectInstances.value).map(item => item.group_id)));
  const groupId = computed(() => {
    const groupId = route.params.groupId ?? 0;
    return Number(groupId);
  });
  const curGroupInfo = computed(() => groupList.value.find(item => item.id === groupId.value));
  const hasSelectedInstances = computed(() => Object.keys(batchSelectInstances.value).length > 0);
  const renderSettings = computed(() => {
    const cloneSettings = _.cloneDeep(settings.value);
    if (groupId.value) {
      cloneSettings.fields = (cloneSettings?.fields || []).filter(item => item.field !== 'group_name');
    }
    return cloneSettings;
  });

  const columns = computed(() => {
    const columns = [
      {
        type: 'selection',
        width: 54,
        label: '',
        fixed: 'left',
      },
      {
        label: t('实例'),
        minWidth: 200,
        fixed: 'left',
        field: 'instance',
        showOverflowTooltip: false,
        render: ({ data }: {data: InfluxDBInstanceModel}) => (
          <div class="instance-box">
            <div
              class="instance-name text-overflow"
              v-overflow-tips>
              <router-link
                to={{
                  name: 'InfluxDBInstDetails',
                  params: {
                    instId: data.id,
                  },
                }}>
                {data.instance_address}
              </router-link>
            </div>
            <div class="cluster-tags">
              <RenderOperationTag data={data} />
              <db-icon
                v-show={!data.isOnline}
                class="cluster-tag"
                svg
                type="yijinyong"
                style="width: 38px; height: 16px;" />
              {
                isRecentDays(data.create_at, 24 * 3)
                  ? <span class="glob-new-tag cluster-tag" data-text="NEW" />
                  : null
              }
            </div>
            <db-icon
              v-bk-tooltips={t('复制实例')}
              class="mt-4"
              type="copy"
              onClick={() => copy(data.instance_address)} />
          </div>
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
        render: ({ data }: {data: InfluxDBInstanceModel}) => <RenderInstanceStatus data={data.status} />,
      },
      {
        label: t('创建人'),
        field: 'creator',
      },
      {
        label: t('部署时间'),
        field: 'create_at',
      },
      {
        label: t('操作'),
        field: '',
        fixed: 'right',
        width: isCN.value ? 140 : 200,
        render: ({ data }: {data: InfluxDBInstanceModel}) => {
          if (data.isOnline) {
            return (
              <>
                <OperationStatusTips data={data}>
                  <bk-button
                    class="mr-8"
                    disabled={data.operationDisabled}
                    loading={tableDataActionLoadingMap.value[data?.id]}
                    text
                    theme="primary"
                    onClick={() => handleShowReplace(data)}>
                    { t('替换') }
                  </bk-button>
                </OperationStatusTips>
                <OperationStatusTips data={data}>
                  <bk-button
                    class="mr-8"
                    disabled={data.operationDisabled}
                    loading={tableDataActionLoadingMap.value[data?.id]}
                    text
                    theme="primary"
                    onClick={() => handleRestart([data])}>
                    { t('重启') }
                  </bk-button>
                </OperationStatusTips>
                <OperationStatusTips data={data}>
                  <bk-button
                    class="mr-8"
                    disabled={data.operationDisabled}
                    loading={tableDataActionLoadingMap.value[data?.id]}
                    text
                    theme="primary"
                    onClick={() => handlDisabled(data)}>
                    { t('禁用') }
                  </bk-button>
                </OperationStatusTips>
              </>
            );
          }
          return (
            <>
              <bk-button
                class="mr-8"
                loading={tableDataActionLoadingMap.value[data?.id]}
                text
                theme="primary"
                onClick={() => handleEnable(data)}>
                { t('启用') }
              </bk-button>
              <bk-button
                class="mr-8"
                loading={tableDataActionLoadingMap.value[data?.id]}
                text
                theme="primary"
                onClick={() => handlDelete(data)}>
                { t('删除') }
              </bk-button>
            </>
          );
        },
      },
    ];
    if (groupId.value === 0) {
      columns.splice(2, 0, {
        label: t('所属分组'),
        field: 'group_name',
      });
    }
    return columns;
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['instance'].includes(item.field as string),
    })),
    checked: [
      'instance',
      'group_name',
      'bk_cloud_name',
      'status',
      'creator',
      'create_at',
    ],
    showLineHeight: true,
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.INFLUXDB_TABLE_SETTINGS, defaultSettings);


  // 设置行样式
  const setRowClass = (row: InfluxDBInstanceModel) => {
    const classList = [row.phase === 'offline' ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    return classList.filter(cls => cls).join(' ');
  };

  const formatInstanceData = (data: Array<InfluxDBInstanceModel>) => data.map((item) => {
    const [ip, port] = item.instance_address.split(':');
    return ({
      ip,
      port: Number(port),
      instance_name: item.instance_name,
      bk_host_id: item.bk_host_id,
      bk_cloud_id: item.bk_cloud_id,
      instance_id: item.id,
    });
  });

  const fetchTableData = (loading?:boolean) => {
    const searchParams = getSearchSelectorParams(search.value);
    tableRef.value?.fetchData(searchParams, {
      group_id: groupId.value === 0 ? undefined : groupId.value,
    }, loading);
    isInit.value = false;
  };

  const handleClearFilters = () => {
    search.value = [];
    fetchTableData();
  };

  const {
    resume: resumeFetchTableData,
  } = useTimeoutPoll(() => fetchTableData(isInit.value), 10000, {
    immediate: false,
  });

  watch(() => route.params.groupId, () => {
    tableRef.value?.updateTableKey();
    fetchTableData();
  });

  onMounted(() => {
    resumeFetchTableData();
  });

  const updateGroupList = (list: InfluxDBGroupItem[] = []) => {
    groupList.value = list;
  };


  const handleCopyAll = (isIp = false) => {
    const list = (tableRef.value.getData() as InfluxDBInstanceModel[]).map(item => item.instance_address);
    if (isIp) {
      copy(list.map(inst => inst.split(':')[0]).join(','));
      return;
    }
    copy(list.join(','));
  };

  const handleCopy = (isIp = false) => {
    const list = Object.values(batchSelectInstances.value).map(item => item.instance_address);
    if (list.length === 0) {
      messageWarn(t('请选择实例'));
      return;
    }

    if (isIp) {
      copy(list.map(inst => inst.split(':')[0]).join(','));
      return;
    }

    copy(list.join(','));
  };

  // 取消节点的选中状态
  const handleRemoveNodeSelect = (instanceId: number) => {
    const checkedMap = { ...batchSelectInstances.value };
    delete checkedMap[instanceId];
    batchSelectInstances.value = checkedMap;

    const index = operationNodeList.value.findIndex(item => item.id === instanceId);
    if (index >= 0) {
      operationNodeList.value.splice(index, 1);
    }

    if (Object.values(checkedMap).length === 0) {
      tableRef.value.clearSelected();
    }
  };

  // 选择单台
  const handleSelect = (data: { checked: boolean, row: InfluxDBInstanceModel }) => {
    const selectedMap = { ...batchSelectInstances.value };
    if (data.checked) {
      selectedMap[data.row.id] = data.row;
    } else {
      delete selectedMap[data.row.id];
    }

    batchSelectInstances.value = selectedMap;
  };

  // 选择所有
  const handleSelectAll = (data:{checked: boolean}) => {
    let selectedMap = { ...batchSelectInstances.value };
    if (data.checked) {
      selectedMap = (tableRef.value.getData() as InfluxDBInstanceModel[]).reduce((result, item) => ({
        ...result,
        [item.id]: item,
      }), {});
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
    if (
      data.id === groupId.value
      || (selectedGroupIds.value.length === 1 && selectedGroupIds.value.includes(data.id))
    ) return;
    moveInstancesToGroup({
      new_group_id: data.id,
      instance_ids: Object.values(batchSelectInstances.value).map(item => item.id),
    })
      .then(() => {
        messageSuccess(t('移动分组成功'));
        fetchTableData();
        batchSelectInstances.value = {};
        eventBus.emit('fetch-group-list');
        tableRef.value.clearSelected();
      });
  };

  const handleShowReplace = (data?: InfluxDBInstanceModel) => {
    operationNodeList.value = data ? [data] : Object.values(batchSelectInstances.value);
    isShowReplace.value = true;
  };

  const handleReplaceSucceeded = () => {
    tableRef.value.clearSelected();
  };

  const handleBatchRestart = () => {
    handleRestart(Object.values(batchSelectInstances.value));
  };

  /**
   * 重启实例
   */
  const handleRestart = (data: InfluxDBInstanceModel[]) => {
    useInfoWithIcon({
      width: 480,
      type: 'warnning',
      confirmTxt: t('重启'),
      title: t('确认重启实例'),
      content: () => (
        <div style="word-break: all;">
          <p>{t('以下实例重启连接将会断开_请谨慎操作')}</p>
          {data.map(item => <p>{item.instance_address}</p>)}
        </div>
      ),
      onConfirm: () => {
        data.forEach((item) => {
          handleChangeTableActionLoading(item.id, true);
        });
        return createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'INFLUXDB_REBOOT',
          details: {
            instance_list: formatInstanceData(data),
          },
        })
          .then((res) => {
            ticketMessage(res.id);
            if (data.length > 1) {
              tableRef.value.clearSelected();
            }
            return true;
          })
          .catch(() => false)
          .finally(() => {
            data.forEach((item) => {
              handleChangeTableActionLoading(item.id, false);
            });
          });
      },
    });
  };

  /**
   * 启用实例
   */
  const handleEnable = (data: InfluxDBInstanceModel) => {
    useInfoWithIcon({
      width: 480,
      type: 'warnning',
      confirmTxt: t('启用'),
      title: t('确认启用该实例'),
      content: () => (
        <div style="word-break: all;">
          <p>{t('实例【instance】启用后将恢复访问', { instance: data.instance_address })}</p>
        </div>
      ),
      onConfirm: () => {
        handleChangeTableActionLoading(data.id, true);
        return createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'INFLUXDB_ENABLE',
          details: {
            instance_list: formatInstanceData([data]),
          },
        })
          .then((res) => {
            ticketMessage(res.id);
            return true;
          })
          .catch(() => false)
          .finally(() => {
            handleChangeTableActionLoading(data.id, false);
          });
      },
    });
  };

  /**
   * 禁用实例
   */
  const handlDisabled = (data: InfluxDBInstanceModel) => {
    useInfoWithIcon({
      width: 480,
      type: 'warnning',
      title: t('确认禁用该实例'),
      confirmTxt: t('禁用'),
      content: () => (
        <div style="word-break: all;">
          <p>{t('实例【instance】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { instance: data.instance_address })}</p>
        </div>
      ),
      onConfirm: () => {
        handleChangeTableActionLoading(data.id, true);
        return createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'INFLUXDB_DISABLE',
          details: {
            instance_list: formatInstanceData([data]),
          },
        })
          .then((res) => {
            ticketMessage(res.id);
            return true;
          })
          .catch(() => false)
          .finally(() => {
            handleChangeTableActionLoading(data.id, false);
          });
      },
    });
  };

  /**
   * 下架实例
   */
  const handlDelete = (data: InfluxDBInstanceModel) => {
    const instanceAddress = data.instance_address;
    useInfoWithIcon({
      width: 480,
      type: 'warnning',
      confirmTheme: 'danger',
      confirmTxt: t('删除'),
      title: t('确定删除该实例'),
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{t('实例【instance】被删除后_将进行以下操作', { instance: instanceAddress })}</p>
          <p>{t('1_删除xx实例', { instance: instanceAddress })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name: instanceAddress })}</p>
        </div>
      ),
      onConfirm: () => {
        handleChangeTableActionLoading(data.id, true);
        return createTicket({
          bk_biz_id: currentBizId,
          ticket_type: 'INFLUXDB_DESTROY',
          details: {
            instance_list: formatInstanceData([data]),
          },
        })
          .then((res) => {
            ticketMessage(res.id);
            return true;
          })
          .catch(() => false)
          .finally(() => {
            handleChangeTableActionLoading(data.id, false);
          });
      },
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
        groupId: groupId.value,
        from: route.name as string,
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

    .bk-button {
      margin-right: 8px;
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

    .cell {
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
