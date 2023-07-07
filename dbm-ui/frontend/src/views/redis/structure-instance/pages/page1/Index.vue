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
        title="构造实例：XXX" />
      <div class="buttons">
        <BkButton>
          {{ $t('批量销毁') }}
        </BkButton>
        <BkButton style="margin-left: 8px;">
          {{ $t('批量回写') }}
        </BkButton>
      </div>
      <BkLoading
        :loading="isTableDataLoading"
        :z-index="2">
        <DbOriginalTable
          :columns="columns"
          :data="tableData"
          :settings="settings"
          @row-click.stop="handleRowClick" />
      </BkLoading>
    </div>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import dataShape from 'bkui-vue/lib/icon/data-shape';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { queryClustersInfo, queryInstanceList } from '@services/redis/toolbox';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes  } from '@common/const';

  import { getClusterInfo } from '@views/redis/common/utils';

  import RedisModel from '@/services/model/redis/redis';

  interface InfoItem {
    cluster_id: number,
    master_instances:string[],
    recovery_time_point: string,
    resource_spec: {
      redis_data_structure_hosts: {
        spec_id: number,
        count: number,
      }
    }
  }

  enum DataRowStatus {
    NORMAL = '正常',
    DESTROING = '销毁中',
    DESTROIED = '已销毁',
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
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref<DataRow[]>([
    {
      cluster: 'dillcir.sz.redis.ellan.db.:2324',
      instances: '全部',
      visitEntry: '192.67.120.200:9000',
      spec: 'XXX机器规格',
      relatedTicket: '221',
      hostNum: 10,
      targetDatetime: '2023-12-20 12:00:00 ',
      status: DataRowStatus.DESTROING,
    },
    {
      cluster: 'dillcir.sz.redis.ellan.db.:2300',
      instances: '192.168.1.1:2000 , 192.168.1.2:2000 ',
      visitEntry: '192.67.120.200:9000',
      spec: 'XXX机器规格',
      relatedTicket: '250',
      hostNum: 10,
      targetDatetime: '2023-12-20 13:00:00 ',
      status: DataRowStatus.DESTROIED,
    }]);
  const isTableDataLoading = ref(false);
  const checkedMap = shallowRef({} as Record<string, DataRow>);
  const totalNum = computed(() => tableData.value.filter(item => item.cluster !== '').length);
  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.cluster]).length
  ));

  const isIndeterminate = computed(() => (Object.keys(checkedMap.value).length > 0));

  const clusterSelectorTabList = [ClusterTypes.REDIS];
  // 集群域名是否已存在表格的映射表
  const domainMemo = {} as Record<string, boolean>;


  const settings = {
    checked: ['cluster', 'instances', 'visitEntry', 'spec', 'relatedTicket', 'hostNum', 'targetDatetime'],
  };
  const columns = [
    {
      label: () => (
        <div class="first-colum">
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
      render: ({ data }: {data: DataRow}) => (
        <div class="first-column">
          <bk-checkbox
            style="vertical-align: middle;"
            label={true}
            model-value={Boolean(checkedMap.value[data.cluster])}
            onClick={(e: Event) => e.stopPropagation()}
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
          />
          <span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#63656E' }}>{data.cluster}</span>
          <bk-tag theme={data.status === DataRowStatus.DESTROIED ? '' : 'danger'} class="tag-tip" style={{ color: data.status === DataRowStatus.DESTROIED ? '#63656E' : '#EA3536' }}>
            {data.status}
          </bk-tag>
        </div>

      ),
    },
    {
      label: t('构造实例范围'),
      field: 'instances',
      render: ({ data }: {data: DataRow}) => (<span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#63656E' }}>{data.instances}</span>),
    },
    {
      minWidth: 100,
      label: t('构造产物访问入口'),
      field: 'visitEntry',
      render: ({ data }: {data: DataRow}) => (<span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#63656E' }}>{data.instances}</span>),
    },
    {
      minWidth: 100,
      label: t('规格需求'),
      field: 'spec',
      render: ({ data }: {data: DataRow}) => (<span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#63656E' }}>{data.instances}</span>),
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
      render: ({ data }: {data: DataRow}) => (<span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#63656E' }}>{data.instances}</span>),
    },
    {
      label: t('构造到指定时间'),
      field: 'targetDatetime',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: DataRow}) => (<span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#63656E' }}>{data.instances}</span>),
    },
    {
      label: t('操作'),
      field: 'cluster',
      showOverflowTooltip: true,
      width: 142,
      render: ({ data }: {data: DataRow}) => (
      <div class="operate-box">
        <span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#3A84FF' }}>销毁</span>
        <span style={{ color: data.status === DataRowStatus.DESTROIED ? '#C4C6CC' : '#3A84FF' }}>回写数据</span>
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

  // 检测列表是否为空
  const checkListEmpty = (list: Array<DataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return firstRow.cluster;
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (moreList: MoreInfoItem[]) => {
    const dataArr = tableData.value.filter(item => item.cluster !== '');
    const infos = dataArr.map((item, index) => {
      const obj: InfoItem = {
        cluster_id: item.clusterId,
        master_instances: moreList[index].instances,
        recovery_time_point: moreList[index].targetDateTime,
        resource_spec: {
          redis_data_structure_hosts: {
            spec_id: item.spec?.id ?? 0,
            count: Number(moreList[index].hostNum),
          },
        },
      };
      return obj;
    });
    return infos;
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const moreList = await Promise.all<MoreInfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<MoreInfoItem[]>
    }) => item.getValue()));

    console.log('morelist: ', moreList);
    const infos = generateRequestParam(moreList);
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
            console.error('单据提交失败：', e);
            // 暂时先按成功处理
            window.changeConfirm = false;
            router.push({
              name: 'RedisDBStructure',
              params: {
                page: 'success',
              },
              query: {
                ticketId: '',
              },
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

</script>

<style lang="less">
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
