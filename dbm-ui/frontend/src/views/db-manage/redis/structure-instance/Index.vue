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
  <div class="redis-struct-ins-page">
    <BkAlert
      closable
      theme="info"
      :title="t('构造实例：通过定点构造产生的实例，可以将实例数据写回原集群或者直接销毁')" />
    <div class="buttons">
      <BkButton
        :disabled="!isIndeterminate"
        @click="handleBatchDestruct">
        {{ t('批量销毁') }}
      </BkButton>
      <BkButton
        class="ml-8"
        :disabled="!isIndeterminate"
        @click="handleBatchDataCopy">
        {{ t('批量回写') }}
      </BkButton>
    </div>
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <PrimaryTable
        :bk-ui-settings="settings"
        class="record-table"
        :columns="columns"
        :data="tableData"
        :max-height="tableHeight"
        :row-class-name="setRowClass"
        row-key="id">
        <template #empty>
          <EmptyStatus
            :is-anomalies="false"
            :is-searching="false"
            @refresh="fetchHostNodes" />
        </template>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          :model-value="pagination.current"
          @change="handleChangePage"
          @limit-change="handeChangeLimit" />
      </div>
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { Checkbox, type PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisRollbackModel from '@services/model/redis/redis-rollback';
  import { getRollbackList } from '@services/source/redisRollback';
  import { createTicket } from '@services/source/ticket';

  import { useDefaultPagination, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import useResetTableHeight from '@views/db-manage/redis/common/hooks/useResetTableHeight';

  const { currentBizId } = useGlobalBizs();
  const handleDeleteSuccess = useTicketMessage();
  const { t } = useI18n();
  const router = useRouter();
  const tableData = ref<RedisRollbackModel[]>([]);
  const isTableDataLoading = ref(false);
  const pagination = ref(useDefaultPagination());
  const tableHeight = ref(500);
  const checkedMap = shallowRef<Record<number, RedisRollbackModel>>({});
  const timer = ref();

  const isSelectedAll = computed(
    () =>
      tableData.value.length > 0 &&
      tableData.value.length === tableData.value.filter((item) => checkedMap.value[item.id]).length,
  );

  const isIndeterminate = computed(() => Object.keys(checkedMap.value).length > 0);

  const settings = {
    checked: [
      'prod_cluster',
      'prod_instance_range',
      'temp_cluster_proxy',
      'specification',
      'related_rollback_bill_id',
      'host_count',
      'recovery_time_point',
    ],
    fields: [
      {
        field: 'prod_cluster',
        label: t('构造的集群'),
      },
      {
        field: 'prod_instance_range',
        label: t('构造实例范围'),
      },
      {
        field: 'temp_cluster_proxy',
        label: t('构造产物访问入口'),
      },
      {
        field: 'specification',
        label: t('规格需求'),
      },
      {
        field: 'related_rollback_bill_id',
        label: t('关联单据'),
      },
      {
        field: 'host_count',
        label: t('构造的主机数量'),
      },
      {
        field: 'recovery_time_point',
        label: t('构造到指定时间'),
      },
    ],
  };

  const { resetTableHeight } = useResetTableHeight(tableHeight, 275);

  onMounted(() => {
    fetchHostNodes();
    resetTableHeight();
  });

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    fetchHostNodes();
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    pagination.value.current = 1;
    fetchHostNodes();
  };

  const fetchHostNodes = async () => {
    const ret = await getRollbackList({
      bk_biz_id: currentBizId,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    });
    tableData.value = ret.results;
    pagination.value.count = ret.count;
  };

  // 渲染多选框
  const renderCheckbox = (data: RedisRollbackModel) => (
    <Checkbox
      checked={Boolean(checkedMap.value[data.id])}
      disabled={!data.isNotDestroyed}
      style='margin-right:8px;vertical-align: middle;'
      onChange={(value: boolean) => handleTableSelectOne(value, data)}
    />
  );

  const handleControlTip = (data: RedisRollbackModel, isShow: boolean) => {
    clearTimeout(timer.value);
    Object.assign(data, {
      isShowInstancesTip: false,
    });
    timer.value = setTimeout(() => {
      Object.assign(data, {
        isShowInstancesTip: isShow,
      });
    }, 500);
  };

  // 渲染首列
  const renderColumnCluster = (data: RedisRollbackModel) => {
    let tipText = '';
    if (data.isDestroyed) {
      tipText = t('已销毁');
    } else if (data.isDestroying) {
      tipText = t('销毁中');
    }
    return (
      <div class='first-column'>
        {data.isDestroying ? (
          <bk-popover
            placement='top'
            theme='light'>
            {{
              content: () => (
                <span>
                  {t('销毁任务正在进行中，跳转')}{' '}
                  <router-link
                    target='_blank'
                    to={{
                      name: 'bizTicketManage',
                      params: {
                        ticketId: data.related_rollback_bill_id,
                      },
                    }}>
                    {t('单据')}
                  </router-link>
                  {t('查看进度')}
                </span>
              ),
              default: () => renderCheckbox(data),
            }}
          </bk-popover>
        ) : (
          renderCheckbox(data)
        )}
        <div class='name'>{data.prod_cluster}</div>
        {(data.isDestroyed || data.isDestroying) && (
          <bk-tag
            class='tag-tip'
            style={{ color: data.isDestroyed ? '#63656E' : '#EA3536' }}
            theme={data.isDestroyed ? undefined : 'danger'}>
            {tipText}
          </bk-tag>
        )}
      </div>
    );
  };

  const renderInstanceRange = (index: number, data: RedisRollbackModel) => {
    const len = data.prod_instance_range.length;
    const showTag = len > 1;
    return showTag ? (
      <bk-popover
        is-show={data.isShowInstancesTip}
        placement='top'
        theme='dark'
        trigger='manual'>
        {{
          content: () => data.prod_instance_range.map((item) => <div>{item}</div>),
          default: () => (
            <div class='instance-box'>
              <div
                class='content'
                onMouseenter={() => handleControlTip(data, true)}
                onMouseleave={() => handleControlTip(data, false)}>
                {data.prod_instance_range.toString()}{' '}
                {showTag && (
                  <div class='tag-box'>
                    <bk-tag>{`+${len - 1}`}</bk-tag>
                  </div>
                )}
              </div>
            </div>
          ),
        }}
      </bk-popover>
    ) : (
      <span>{data.prod_instance_range.toString()}</span>
    );
  };

  const columns: PrimaryTableCol[] = [
    {
      cell: (_, { row }) => renderColumnCluster(row as RedisRollbackModel),
      colKey: 'prod_cluster',
      minWidth: 150,
      title: () => (
        <div class='first-column'>
          <Checkbox
            checked={isSelectedAll.value}
            indeterminate={isSelectedAll.value ? false : isIndeterminate.value}
            onChange={handleSelectPageAll}
          />
          {t('构造的集群')}
        </div>
      ),
    },
    {
      cell: (_, { row, rowIndex }) => renderInstanceRange(rowIndex, row as RedisRollbackModel),
      colKey: 'prod_instance_range',
      minWidth: 150,
      title: t('构造实例范围'),
      width: 250,
    },
    {
      colKey: 'temp_cluster_proxy',
      minWidth: 130,
      title: t('构造产物访问入口'),
    },
    {
      cell: (_, { row }) => <span>{row.specification.name}</span>,
      colKey: 'specification',
      minWidth: 100,
      title: t('规格需求'),
    },
    {
      cell: (_, { row }) =>
        row.related_rollback_bill_id ? (
          <router-link
            target='_blank'
            to={{
              name: 'bizTicketManage',
              params: {
                ticketId: row.related_rollback_bill_id,
              },
            }}>
            {row.related_rollback_bill_id}
          </router-link>
        ) : (
          '--'
        ),
      colKey: 'related_rollback_bill_id',
      minWidth: 100,
      title: t('关联单据'),
      width: 110,
    },
    {
      colKey: 'host_count',
      minWidth: 120,
      title: t('构造的主机数量'),
      width: 120,
    },
    {
      cell: (_, { row }) => <span>{row.recoveryTimePointDisplay}</span>,
      colKey: 'recovery_time_point',
      minWidth: 150,
      title: t('构造到指定时间'),
    },
    {
      cell: (_, { row }) => (
        <div
          class='operate-box'
          style={{ color: row.isNotDestroyed ? '#3A84FF' : '#C4C6CC' }}>
          <bk-button
            text
            theme='primary'
            onClick={() => handleClickDestructItem(row as RedisRollbackModel)}>
            {t('销毁')}
          </bk-button>
          <bk-button
            style='margin-left:10px;'
            text
            theme='primary'
            onClick={() => handleClickDataCopy(row as RedisRollbackModel)}>
            {t('回写数据')}
          </bk-button>
        </div>
      ),
      colKey: 'row-operation',
      fixed: 'right',
      minWidth: 140,
      title: t('操作'),
      width: 180,
    },
  ];

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of tableData.value) {
      if (item.isNotDestroyed) {
        if (checked) {
          lastCheckMap[item.id] = item;
        } else {
          delete lastCheckMap[item.id];
        }
      }
    }
    checkedMap.value = lastCheckMap;
  };

  const handleTableSelectOne = (checked: boolean, data: RedisRollbackModel) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.id] = data;
    } else {
      delete lastCheckMap[data.id];
    }
    checkedMap.value = lastCheckMap;
  };

  // 获取有效的选中列表
  const getCheckedValidList = () => {
    const list = Object.values(checkedMap.value);
    return list.filter((item) => item.isNotDestroyed);
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (rowData?: RedisRollbackModel) => {
    const dataArr = getCheckedValidList();
    if (!rowData) {
      const infos = dataArr.map((item) => {
        const { bk_cloud_id, related_rollback_bill_id } = item;
        const obj = {
          bk_cloud_id,
          cluster_id: item.prod_cluster_id,
          display_info: {
            temp_cluster_proxy: item.temp_cluster_proxy,
          },
          related_rollback_bill_id,
        };
        return obj;
      });
      return infos;
    }
    return [
      {
        bk_cloud_id: rowData.bk_cloud_id,
        cluster_id: rowData.prod_cluster_id,
        display_info: {
          temp_cluster_proxy: rowData.temp_cluster_proxy,
        },
        related_rollback_bill_id: rowData.related_rollback_bill_id,
      },
    ];
  };

  // 设置行样式
  const setRowClass = ({ row }: { row: RedisRollbackModel }) => (row.isDestroyed ? 'disable-color' : 'normal-color');

  // 批量销毁
  const handleBatchDestruct = () => {
    const infos = generateRequestParam();
    const params = {
      bk_biz_id: currentBizId,
      details: {
        infos,
      },
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
    };
    InfoBox({
      confirmText: t('删除'),
      onConfirm: () => {
        createTicket(params).then((data) => {
          const ticketId = data.id;
          handleDeleteSuccess(ticketId);
        });
      },
      subTitle: t('销毁后将不可再恢复，请谨慎操作！'),
      title: t('确认销毁 n 个集群的构造实例？', { n: infos.length }),
      width: 480,
    });
  };

  // 批量回写
  const handleBatchDataCopy = () => {
    const list = Object.values(checkedMap.value);
    router.push({
      name: TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
      query: {
        domains: list.map((item) => item.temp_cluster_proxy).join(','),
      },
    });
  };

  // 销毁
  const handleClickDestructItem = (data: RedisRollbackModel) => {
    if (!data.isNotDestroyed) {
      return;
    }
    const infos = generateRequestParam(data);
    const params = {
      bk_biz_id: currentBizId,
      details: {
        infos,
      },
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
    };
    InfoBox({
      confirmText: t('删除'),
      onConfirm: () => {
        createTicket(params).then((data) => {
          const ticketId = data.id;
          handleDeleteSuccess(ticketId);
        });
      },
      subTitle: t('销毁后将不可再恢复，请谨慎操作！'),
      title: t('确认销毁 n 个集群的构造实例？', { n: 1 }),
      width: 480,
    });
  };

  // 回写数据
  const handleClickDataCopy = (data: RedisRollbackModel) => {
    if (!data.isNotDestroyed) {
      return;
    }
    router.push({
      name: TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
      query: {
        domains: data.temp_cluster_proxy,
      },
    });
  };
</script>

<style lang="less" scoped>
  .record-table {
    :deep(.normal-color) {
      td {
        color: #63656e;
      }
    }

    :deep(.disable-color) {
      td {
        color: #c4c6cc;
      }
    }

    :deep(.first-column) {
      display: flex;
      align-items: center;

      .name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .tag-tip {
        padding: 1px 4px;
        font-weight: 700;
        transform: scale(0.83, 0.83);
      }
    }

    :deep(.operate-box) {
      cursor: pointer;
    }

    :deep(.instance-box) {
      position: relative;
      width: 100%;
      padding-right: 4px;
      overflow: hidden;

      .content {
        width: 100%;
        padding-right: 20px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .tag-box {
        position: absolute;
        top: 0;
        right: -10px;

        .bk-tag {
          padding: 0 6px;
          font-size: 12px;
          transform: scale(0.83, 0.83);
        }
      }
    }
  }

  .redis-struct-ins-page {
    padding-bottom: 20px;

    .buttons {
      margin: 16px 0;
    }

    .table-footer {
      position: relative;
      z-index: 1;
      display: flex;
      height: 60px;
      padding: 0 16px;
      margin-top: -1px;
      background: #fff;
      border-top: 1px solid var(--td-component-border);
      align-items: center;

      :deep(.bk-pagination) {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }
</style>
