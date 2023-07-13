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
          :disabled="!isBatchSelected"
          @click="handleBatchDestruct">
          {{ $t('批量销毁') }}
        </BkButton>
        <BkButton
          :disabled="!isBatchSelected"
          style="margin-left: 8px;"
          @click="handleBatchDataCopy">
          {{ $t('批量回写') }}
        </BkButton>
      </div>
      <BkLoading
        :loading="isTableDataLoading"
        :z-index="2">
        <DbOriginalTable
          :columns="columns"
          :data="tableData"
          :row-class="setRowClass"
          :settings="settings"
          @row-click.stop="handleRowClick" />
      </BkLoading>
    </div>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes  } from '@common/const';


  interface InfoItem {
    related_rollback_bill_id: number,
    prod_cluster: string,
    bk_cloud_id: number,
  }

  enum DataRowStatus {
    NORMAL = 'NORMAL',
    DESTROING = 'DESTROING',
    DESTROIED = 'DESTROIED',
  }

  interface DataRow {
    cluster: string;
    instances: string;
    visitEntry: string;
    spec: string;
    relatedTicket: string;
    hostNum: number;
    targetDatetime: string;
    status: DataRowStatus;
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isSubmitting  = ref(false);
  const tableData = ref<DataRow[]>([]);
  const isTableDataLoading = ref(false);
  const checkedMap = shallowRef({} as Record<string, DataRow>);
  const totalNum = computed(() => tableData.value.filter(item => item.cluster !== '').length);
  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.cluster]).length
  ));

  const isIndeterminate = computed(() => (Object.keys(checkedMap.value).length > 0));
  const isBatchSelected = computed(() => Object.keys(checkedMap.value).length > 0
    && tableData.value.filter(item => item.status !== DataRowStatus.NORMAL).length !== tableData.value.length);

  const settings = {
    checked: ['cluster', 'instances', 'visitEntry', 'spec', 'relatedTicket', 'hostNum', 'targetDatetime'],
  };

  // 渲染多选框
  const renderCheckbox = (data: DataRow) => (
    <bk-checkbox
      disabled={data.status !== DataRowStatus.NORMAL}
      model-value={Boolean(checkedMap.value[data.cluster])}
      style="margin-right:8px;vertical-align: middle;"
      onClick={(e: Event) => e.stopPropagation()}
      onChange={(value: boolean) => handleTableSelectOne(value, data)}
    />
  );

  // 渲染首列
  const renderColumnCluster = (data: DataRow) => {
    const isDestroied = data.status === DataRowStatus.DESTROIED;
    const isDestroing = data.status === DataRowStatus.DESTROING;
    return (
    <div class="first-column">
      {isDestroing
        ? <bk-popover theme="light">
            {{
              default: () => renderCheckbox(data),
              content: () => (<span>{t('销毁任务正在进行中，跳转')} <span style="color:#3A84FF;cursor:pointer;" onClick={() => handleGoTicket(data.relatedTicket)}>t('我的服务单')</span> t('查看进度')</span>),
            }}
          </bk-popover>
        : renderCheckbox(data)
      }
      <span>{data.cluster}</span>
      {(isDestroied || isDestroing) && <bk-tag theme={isDestroied ? undefined : 'danger'} class="tag-tip" style={{ color: isDestroied ? '#63656E' : '#EA3536' }}>
        {data.status}
      </bk-tag>}
    </div>);
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
      field: 'cluster',
      showOverflowTooltip: true,
      width: 240,
      render: ({ data }: {data: DataRow}) => renderColumnCluster(data),
    },
    {
      label: t('构造实例范围'),
      field: 'instances',
      render: ({ data }: {data: DataRow}) => (<span>{data.instances}</span>),
    },
    {
      minWidth: 100,
      label: t('构造产物访问入口'),
      field: 'visitEntry',
    },
    {
      minWidth: 100,
      label: t('规格需求'),
      field: 'spec',
    },
    {
      label: t('关联单据'),
      field: 'relatedTicket',
      showOverflowTooltip: true,
      width: 105,
      render: ({ data }: {data: DataRow}) => <span style="color:#3A84FF;">{data.relatedTicket}</span>,
    },
    {
      label: t('构造的主机数量'),
      field: 'hostNum',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('构造到指定时间'),
      field: 'targetDatetime',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('操作'),
      field: 'cluster',
      showOverflowTooltip: true,
      width: 142,
      render: ({ data }: {data: DataRow}) => (
      <div class="operate-box" style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#3A84FF' }}>
        <span onClick={() => handleClickDestructItem(data)}>{t('销毁')}</span>
        <span onClick={() => handleClickDataCopy(data)}>{t('回写数据')}</span>
      </div>),
    },
  ];

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of tableData.value) {
      if (checked) {
        lastCheckMap[item.cluster] = item;
      } else {
        delete lastCheckMap[item.cluster];
      }
    }
    checkedMap.value = lastCheckMap;
  };

  const handleTableSelectOne = (checked: boolean, data: DataRow) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.cluster] = data;
    } else {
      delete lastCheckMap[data.cluster];
    }
    checkedMap.value = lastCheckMap;
  };

  const handleRowClick = (key: any, data: DataRow) => {
    const checked = checkedMap.value[data.cluster];
    handleTableSelectOne(!checked, data);
  };

  // 获取有效的选中列表
  const getCheckedValidList = () => {
    const list = Object.values(checkedMap.value);
    return list.filter(item => item.status === DataRowStatus.NORMAL);
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (rowData?: DataRow) => {
    const dataArr = getCheckedValidList();
    if (!rowData) {
      const infos = dataArr.map((item) => {
        const obj: InfoItem = {
          related_rollback_bill_id: 0,
          prod_cluster: item.cluster,
          bk_cloud_id: 0,
        };
        return obj;
      });
      return infos;
    }
    return [
      {
        related_rollback_bill_id: 0,
        prod_cluster: rowData.cluster,
        bk_cloud_id: 0,
      },
    ];
  };

  // 设置行样式
  const setRowClass = (row: DataRow) => (row.status === DataRowStatus.DESTROIED ? 'disable-color' : 'normal-color');

  const handleGoTicket = (ticketId: string) => {
    const route = router.resolve({
      name: 'SelfServiceMyTickets',
      query: {
        filterId: ticketId,
      },
    });
    window.open(route.href);
  };

  const handleBatchDestruct = () => {
    const infos = generateRequestParam();
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
      details: {
        infos,
      },
    };
    console.log(params);
  };

  const handleBatchDataCopy = () => {
    console.log(checkedMap.value);
  };

  const handleClickDestructItem = (data: DataRow) => {
    console.log(data);
    const infos = generateRequestParam(data);
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE,
      details: {
        infos,
      },
    };
    console.log(params);
  };

  const handleClickDataCopy = (data: DataRow) => {
    console.log(data);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = generateRequestParam();
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_DATA_STRUCTURE,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    console.log('submit params: ', params);
    InfoBox({
      title: t('确认定点构造 n 个集群？', { n: totalNum.value }),
      subTitle: t('集群上的数据将会全部构造至指定的新机器共 n GB，预计时长 m 分钟', { n: 0, m: 0 }),
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisDBStructure',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            // 目前后台还未调通
            console.error('submit structure instance ticket error：', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

</script>

<style lang="less" scoped>

.normal-color {
  td {
    .cell {
      color: #63656E !important;
    }
  }
}

.disable-color {
  td {
    .cell {
      color: #C4C6CC !important;
    }
  }
}

.first-column {
  display: flex;
  align-items: center;

  .tag-tip {
    padding: 1px 4px;
    font-weight: 700;
    transform : scale(0.83,0.83);
  }
}

.operate-box {
  display: flex;
  width: 80px;
  justify-content: space-between;

  span {
    cursor: pointer;
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
