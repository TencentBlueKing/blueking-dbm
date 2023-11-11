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
  <div class="dbha-events">
    <div class="dbha-events-operations">
      <DbSearchSelect
        v-model="filters.search"
        class="mr-8"
        :data="searchSelectData"
        style="width: 420px;"
        unique-select
        value-behavior="need-key" />
      <BkDatePicker
        v-model="filters.daterange"
        append-to-body
        clearable
        :placeholder="$t('请选择')"
        style="width: 340px;"
        type="datetimerange" />
    </div>
    <BkLoading :loading="isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        :is-searching="isSearching"
        :max-height="tableMaxHeight"
        :settings="settings"
        @clear-search="handleClearSearch"
        @refresh="fetchTableData"
        @setting-change="updateTableSettings" />
    </BkLoading>
  </div>

  <BkSideslider
    v-model:is-show="logState.isShow"
    class="log-sideslider"
    quick-close
    render-directive="if"
    :width="960">
    <template #header>
      <div class="log-sideslider-header">
        <span
          v-overflow-tips
          class="text-overflow">
          {{ logState.title }}
        </span>
        <div class="infos">
          <template v-if="logState.data.result_info?.text">
            <BkTag
              class="mg-0"
              :theme="logState.data.result_info.theme">
              {{ logState.data.result_info.text }}
            </BkTag>
          </template>
          <span>
            {{ $t('总耗时') }}:
            {{ logState.data.cost_time }}
          </span>
        </div>
      </div>
    </template>
    <SwtichEventDetatils :uid="logState.data.uid" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { format, subDays } from 'date-fns';
  import { useI18n } from 'vue-i18n';

  import { getBizs } from '@services/common';
  import { getEventSwitchList } from '@services/eventSwitch';
  import type { EventSwtichItem } from '@services/types/eventSwitch';

  import { useTableMaxHeight, useTableSettings } from '@hooks';

  import DbStatus from '@components/db-status/index.vue';

  import { getCostTimeDisplay } from '@utils';

  import SwtichEventDetatils from '../components/SwtichEventDetatils.vue';

  import { UserPersonalSettings } from '@/common/const';
  import type { SearchSelectValues } from '@/types/bkui-vue';

  // type TimeType = string | Date;

  interface BizItem {
    id: number,
    name: string
  }

  interface TableItem extends EventSwtichItem {
    cost_time: string,
    result_info: {
      text: string,
      theme?: 'success' | 'warning' | 'danger' | 'info'
    }
  }

  const router = useRouter();
  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(204);

  const isAnomalies = ref(false);
  const isLoading = ref(false);
  const tableData = shallowRef<TableItem[]>([]);
  const bizList = shallowRef<BizItem[]>([]);
  const columns = [
    {
      label: t('业务'),
      field: 'bk_biz_name',
    },
    {
      label: t('集群域名'),
      field: 'cluster',
      render: ({ data }: { data: TableItem }) => <a href="javascript:" onClick={handleToCluster.bind(null, data)}>{data.cluster}</a>,
    },
    {
      label: t('实例类型'),
      field: 'db_type',
    },
    {
      label: t('实例角色'),
      field: 'db_role',
      render: ({ cell }: { cell: string }) => cell || '--',
    },
    {
      label: t('故障IP'),
      field: 'ip',
    },
    {
      label: t('故障Port'),
      field: 'port',
    },
    {
      label: t('新IP'),
      field: 'slave_ip',
      render: ({ cell }: { cell: string }) => cell || '--',
    },
    {
      label: t('新Port'),
      field: 'slave_port',
    },
    {
      label: t('开始时间'),
      field: 'switch_start_time',
    },
    {
      label: t('结束时间'),
      field: 'switch_finished_time',
    },
    {
      label: t('耗时'),
      field: 'cost_time',
    },
    {
      label: t('切换结果'),
      field: 'switch_result',
      render: ({ cell, data }: { cell: string, data: TableItem }) => {
        if (['failed', 'success'].includes(cell)) {
          return <DbStatus theme={data.result_info.theme}>{data.result_info.text}</DbStatus>;
        }

        return cell || '--';
      },
    },
    {
      label: t('切换原因'),
      field: 'confirm_result',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string }) => (
        <div class="text-overflow" v-overflow-tips={{ content: cell, maxWidth: 400 }}>
          {cell || '--'}
        </div>
      ),
    },
    {
      label: t('操作'),
      field: '',
      width: 100,
      render: ({ data }: { data: TableItem }) => (
        <bk-button
          text
          theme="primary"
          onClick={handleShowDetails.bind(this, data)}>
          { t('详情') }
        </bk-button>
      ),
    },
  ];
  const filters = reactive({
    search: [] as SearchSelectValues,
    daterange: [subDays(new Date(), 6).toISOString(), new Date().toISOString()] as [string, string],
  });
  const filterParams = computed(() => {
    const params: Record<string, any> = {};
    const { search, daterange } = filters;
    if (search.length > 0) {
      const [bizSearchItem] = search;
      params.app = bizSearchItem?.values?.[0]?.id;
    }

    const [start, end] = daterange;
    if (start && end) {
      params.switch_start_time = format(new Date(start), 'yyyy-MM-dd HH:mm:ss');
      params.switch_finished_time = format(new Date(end), 'yyyy-MM-dd HH:mm:ss');
    }


    return params;
  });
  // eslint-disable-next-line max-len
  const isSearching = computed(() => filters.search.length > 0 ||  filters.daterange.length > 0);
  const searchSelectData = computed(() => [{
    name: t('业务'),
    id: 'app',
    children: bizList.value,
  }]);
  const logState = reactive({
    isShow: false,
    title: '',
    data: {} as TableItem,
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['bk_biz_name', 'cluster', 'ip', 'port', 'slave_ip', 'slave_port'].includes(item.field as string),
    })),
    checked: columns.map(item => item.field).filter(key => !!key) as string[],
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.DBHA_SWITCH_EVENTS, defaultSettings);

  const handleClearSearch = () => {
    filters.search = [];
    filters.daterange = ['', ''];
  };

  const fetchBizList = () => {
    getBizs()
      .then((res) => {
        bizList.value = res.map(item => ({
          id: item.bk_biz_id,
          name: item.name,
        }));
      });
  };
  fetchBizList();

  const fetchTableData = () => {
    isLoading.value = true;
    getEventSwitchList(filterParams.value)
      .then((res) => {
        isAnomalies.value = false;
        tableData.value = res.map((item) => {
          let costTime = '--';
          if (item.switch_start_time && item.switch_finished_time) {
            const endTime = (new Date(item.switch_finished_time)).getTime();
            const startTime = (new Date(item.switch_start_time)).getTime();
            costTime = getCostTimeDisplay((endTime - startTime) / 1000);
          }

          const resultInfo = {
            text: item.switch_result,
            theme: 'warning',
          };
          if (['failed', 'success'].includes(item.switch_result)) {
            resultInfo.text = item.switch_result === 'success' ? t('切换成功') : t('切换失败');
            resultInfo.theme = item.switch_result === 'success' ? 'success' : 'danger';
          }

          return {
            ...item,
            cost_time: costTime,
            result_info: resultInfo,
          };
        }) as TableItem[];
      })
      .catch(() => {
        tableData.value = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
  fetchTableData();

  watch(filterParams, () => {
    fetchTableData();
  });

  const handleShowDetails = (data: TableItem) => {
    logState.isShow = true;
    logState.data = data;
    logState.title = data.cluster ? t('xx切换日志详情', { cluster: data.cluster }) : '';
  };

  const handleToCluster = (data: TableItem) => {
    const { cluster_type: clusterType } = data.cluster_info;
    let routeName = '';
    if (clusterType === 'tendbsingle') {
      routeName = 'DatabaseTendbsingle';
    } else if (clusterType === 'tendbha') {
      routeName = 'DatabaseTendbha';
    } else if (['TwemproxyRedisInstance', 'PredixyTendisplusCluster'].includes(clusterType)) {
      routeName = 'DatabaseRedis';
    } else if (clusterType === 'es') {
      routeName = 'EsManage';
    } else if (clusterType === 'hdfs') {
      routeName = 'HdfsManage';
    } else if (clusterType === 'kafka') {
      routeName = 'KafkaManage';
    }

    router.push({
      name: routeName,
      params: {
        bizId: data.bk_biz_id,
      },
      query: {
        cluster_id: data.cluster_info.id,
      },
    });
  };
</script>

<style lang="less" scoped>
.dbha-events {
  .dbha-events-operations {
    display: flex;
    margin-bottom: 16px;
  }
}

.log-sideslider {
  :deep(.bk-modal-content) {
    height: 100%;
  }

  .log-sideslider-header {
    display: flex;
    align-items: center;
    overflow: hidden;

    .infos {
      display: flex;
      padding-right: 30px;
      padding-left: 8px;
      align-items: center;
      flex-shrink: 0;
    }
  }
}
</style>
