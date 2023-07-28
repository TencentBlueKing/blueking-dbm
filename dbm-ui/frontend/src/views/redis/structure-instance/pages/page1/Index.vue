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
  <SmartAction>
    <div class="redis-struct-ins-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('构造实例：XXX')" />
      <div class="buttons">
        <BkButton
          :disabled="!isIndeterminate"
          @click="handleBatchDestruct">
          {{ $t('批量销毁') }}
        </BkButton>
        <BkButton
          class="ml-8"
          :disabled="!isIndeterminate"
          @click="handleBatchDataCopy">
          {{ $t('批量回写') }}
        </BkButton>
      </div>
      <BkLoading
        :loading="isTableDataLoading"
        :z-index="2">
        <DbOriginalTable
          class="record-table"
          :columns="columns"
          :data="tableData"
          :pagination="pagination"
          :row-class="setRowClass"
          :settings="settings"
          @page-limit-change="handeChangeLimit"
          @page-value-change="handleChangePage"
          @refresh="fetchHostNodes"
          @row-click.stop="handleRowClick" />
      </BkLoading>
    </div>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisRollbackModel, { DestroyStatus } from '@services/model/redis/redis-rollback';
  import { getRollbackList } from '@services/redis/toolbox';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useDefaultPagination, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { LocalStorageKeys, TicketTypes  } from '@common/const';


  interface InfoItem {
    related_rollback_bill_id: number,
    prod_cluster: string,
    bk_cloud_id: number,
  }

  const { currentBizId } = useGlobalBizs();
  const handleDeleteSuccess = useTicketMessage();
  const { t } = useI18n();
  const router = useRouter();
  const tableData = shallowRef<RedisRollbackModel[]>([]);
  const isTableDataLoading = ref(false);
  const pagination = ref(useDefaultPagination());
  const checkedMap = shallowRef<Record<string, RedisRollbackModel>>({});

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.prod_cluster]).length
  ));

  const isIndeterminate = computed(() => (Object.keys(checkedMap.value).length > 0));

  const settings = {
    checked: ['cluster', 'instances', 'visitEntry', 'spec', 'relatedTicket', 'hostNum', 'targetDatetime'],
  };

  onMounted(() => {
    fetchHostNodes();
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
      limit: pagination.value.limit,
      offset: pagination.value.current,
    });
    tableData.value = ret.results;
    pagination.value.count = ret.count;
  };

  // 渲染多选框
  const renderCheckbox = (data: RedisRollbackModel) => (
    <bk-checkbox
      disabled={data.destroyed_status !== DestroyStatus.NOT_DESTROYED}
      model-value={Boolean(checkedMap.value[data.prod_cluster])}
      style="margin-right:8px;vertical-align: middle;"
      onClick={(e: Event) => e.stopPropagation()}
      onChange={(value: boolean) => handleTableSelectOne(value, data)}
    />
  );

  // 渲染首列
  const renderColumnCluster = (data: RedisRollbackModel) => {
    const isDestroied = data.destroyed_status === DestroyStatus.DESTROYED;
    const isDestroing = data.destroyed_status === DestroyStatus.DESTROYING;
    const tipText = isDestroied ? t('已销毁') : isDestroing ? t('销毁中') : '';
    return (
    <div class="first-column">
      {isDestroing
        ? <bk-popover theme="light" placement="top">
            {{
              default: () => renderCheckbox(data),
              content: () => (<span>{t('销毁任务正在进行中，跳转')} <span style="color:#3A84FF;cursor:pointer;" onClick={() => handleGoTicket(data.related_rollback_bill_id)}>{t('我的服务单')}</span>{t('查看进度')}</span>),
            }}
          </bk-popover>
        : renderCheckbox(data)
      }
      <div class="name">{data.prod_cluster}</div>
      {(isDestroied || isDestroing) && <bk-tag theme={isDestroied ? undefined : 'danger'} class="tag-tip" style={{ color: isDestroied ? '#63656E' : '#EA3536' }}>
        {tipText}
      </bk-tag>}
    </div>);
  };

  const renderInstanceRange = (data: RedisRollbackModel) => {
    const len = data.prod_instance_range.length;
    const showTag = len > 1;
    return showTag ? (
      <bk-popover placement="top" theme="dark">
            {{
              default: () => (
                <div class="instance-box">
                  <div class="content">{data.prod_instance_range.toString()} {showTag && <div class="tag-box"><bk-tag>{`+${len - 1}`}</bk-tag></div>}</div>
                </div>
              ),
              content: () => data.prod_instance_range.map(item => (<div>{item}</div>)),
            }}
          </bk-popover>
      ) : (
      <span>{data.prod_instance_range.toString()}</span>
    );
  };

  const columns = [
    {
      label: () => (
        <div class="first-column">
          <bk-checkbox
            label={true}
            indeterminate={isSelectedAll.value ? false : isIndeterminate.value}
            model-value={isSelectedAll.value}
            onClick={(e: Event) => e.stopPropagation()}
            onChange={handleSelectPageAll}
        />
          {t('构造的集群')}
        </div>
       ),
      field: 'prod_cluster',
      showOverflowTooltip: false,
      minWidth: 150,
      render: ({ data }: {data: RedisRollbackModel}) => renderColumnCluster(data),
    },
    {
      label: t('构造实例范围'),
      field: 'prod_instance_range',
      showOverflowTooltip: false,
      minWidth: 150,
      width: 250,
      render: ({ data }: {data: RedisRollbackModel}) => renderInstanceRange(data),
    },
    {
      label: t('构造产物访问入口'),
      field: 'temp_cluster_proxy',
      minWidth: 130,
    },
    {
      label: t('规格需求'),
      field: 'specification',
      minWidth: 100,
      render: ({ data }: {data: RedisRollbackModel}) => (<span>{data.specification.name}</span>),
    },
    {
      label: t('关联单据'),
      field: 'related_rollback_bill_id',
      showOverflowTooltip: true,
      minWidth: 100,
      width: 110,
      render: ({ data }: {data: RedisRollbackModel}) => <span style="color:#3A84FF;">{data.related_rollback_bill_id}</span>,
    },
    {
      label: t('构造的主机数量'),
      field: 'host_count',
      showOverflowTooltip: true,
      minWidth: 120,
      width: 120,
    },
    {
      label: t('构造到指定时间'),
      field: 'recovery_time_point',
      showOverflowTooltip: true,
      minWidth: 150,
    },
    {
      label: t('操作'),
      field: '',
      fixed: 'right',
      showOverflowTooltip: true,
      minWidth: 140,
      width: 180,
      render: ({ data }: {data: RedisRollbackModel}) => (
      <div class="operate-box" style={{ color: data.destroyed_status === DestroyStatus.NOT_DESTROYED ? '#3A84FF' : '#C4C6CC' }}>
        <span onClick={() => handleClickDestructItem(data)}>{t('销毁')}</span>
        <span onClick={() => handleClickDataCopy(data)} style="margin-left:10px;">{t('回写数据')}</span>
      </div>),
    },
  ];

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of tableData.value) {
      if (item.destroyed_status === DestroyStatus.NOT_DESTROYED) {
        if (checked) {
          lastCheckMap[item.prod_cluster] = item;
        } else {
          delete lastCheckMap[item.prod_cluster];
        }
      }
    }
    checkedMap.value = lastCheckMap;
  };

  const handleTableSelectOne = (checked: boolean, data: RedisRollbackModel) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.prod_cluster] = data;
    } else {
      delete lastCheckMap[data.prod_cluster];
    }
    checkedMap.value = lastCheckMap;
  };

  const handleRowClick = (key: number, data: RedisRollbackModel) => {
    if (data.destroyed_status !== DestroyStatus.NOT_DESTROYED) {
      return;
    }
    const checked = checkedMap.value[data.prod_cluster];
    handleTableSelectOne(!checked, data);
  };

  // 获取有效的选中列表
  const getCheckedValidList = () => {
    const list = Object.values(checkedMap.value);
    return list.filter(item => item.destroyed_status === DestroyStatus.NOT_DESTROYED);
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (rowData?: RedisRollbackModel) => {
    const dataArr = getCheckedValidList();
    if (!rowData) {
      const infos = dataArr.map((item) => {
        const {
          related_rollback_bill_id,
          prod_cluster,
          bk_cloud_id,
        } = item;
        const obj = {
          related_rollback_bill_id,
          prod_cluster,
          bk_cloud_id,
        };
        return obj;
      });
      return infos;
    }
    return [
      {
        related_rollback_bill_id: rowData.related_rollback_bill_id,
        prod_cluster: rowData.prod_cluster,
        bk_cloud_id: rowData.bk_cloud_id,
      },
    ];
  };

  // 设置行样式
  const setRowClass = (row: RedisRollbackModel) => (row.destroyed_status === DestroyStatus.DESTROYED ? 'disable-color' : 'normal-color');

  const handleGoTicket = (ticketId: number) => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        filterId: ticketId,
      },
    });
    window.open(route.href);
  };

  // 批量销毁
  const handleBatchDestruct = () => {
    const infos = generateRequestParam();
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
      details: {
        infos,
      },
    };
    InfoBox({
      title: t('确认销毁 n 个集群的构造实例？', { n: infos.length }),
      subTitle: t('销毁后将不可再恢复，请谨慎操作！'),
      width: 480,
      infoType: 'warning',
      confirmText: t('删除'),
      onConfirm: () => {
        createTicket(params)
          .then((data) => {
            const ticketId = data.id;
            handleDeleteSuccess(ticketId);
          })
          .catch((e) => {
            console.error('destroy instance submit ticket error: ', e);
          });
      } });
  };

  // 批量回写
  const handleBatchDataCopy = () => {
    const list = Object.values(checkedMap.value);
    localStorage.setItem(LocalStorageKeys.ROLLBACK_LIST, JSON.stringify(list));
    router.push({
      name: 'RedisRecoverFromInstance',
    });
  };

  // 销毁
  const handleClickDestructItem = (data: RedisRollbackModel) => {
    if (data.destroyed_status !== DestroyStatus.NOT_DESTROYED) {
      return;
    }
    const infos = generateRequestParam(data);
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
      details: {
        infos,
      },
    };
    InfoBox({
      title: t('确认销毁 n 个集群的构造实例？', { n: 1 }),
      subTitle: t('销毁后将不可再恢复，请谨慎操作！'),
      width: 480,
      infoType: 'warning',
      confirmText: t('删除'),
      onConfirm: () => {
        createTicket(params)
          .then((data) => {
            const ticketId = data.id;
            handleDeleteSuccess(ticketId);
          })
          .catch((e) => {
            console.error('destroy instance submit ticket error: ', e);
          });
      } });
  };

  // 回写数据
  const handleClickDataCopy = (data: RedisRollbackModel) => {
    if (data.destroyed_status !== DestroyStatus.NOT_DESTROYED) {
      return;
    }
    localStorage.setItem(LocalStorageKeys.ROLLBACK_LIST, JSON.stringify([data]));
    router.push({
      name: 'RedisRecoverFromInstance',
    });
  };

</script>

<style lang="less" scoped>


.record-table {
  :deep(.normal-color) {
    .cell {
      color: #63656E;
    }
  }

  :deep(.disable-color) {
    .cell {
      color: #C4C6CC;
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
      transform : scale(0.83,0.83);
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

    .tag-box{
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
