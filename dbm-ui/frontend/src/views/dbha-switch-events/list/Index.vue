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
      <BkDatePicker
        v-model="filterDateRang"
        append-to-body
        clearable
        :placeholder="t('请选择')"
        style="width: 340px"
        type="datetimerange"
        @change="fetchTableData" />
    </div>
    <BkLoading :loading="isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        :max-height="tableMaxHeight"
        :settings="settings"
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
            {{ t('总耗时') }}:
            {{ logState.data.cost_time }}
          </span>
        </div>
      </div>
    </template>
    <SwtichEventDetatils
      :is-active="logState.isShow"
      :uid="logState.data.uid" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import { getEventSwitchList } from '@services/source/dbha';

  import { useTableMaxHeight, useTableSettings } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { getCostTimeDisplay, utcDisplayTime } from '@utils';

  import SwtichEventDetatils from './components/SwtichEventDetatils.vue';

  type EventSwtichItem = ServiceReturnType<typeof getEventSwitchList>[number];

  interface TableItem extends EventSwtichItem {
    cost_time: string;
    result_info: {
      text: string;
      theme?: 'success' | 'warning' | 'danger' | 'info';
    };
  }

  const router = useRouter();
  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(204);

  const isAnomalies = ref(false);
  const isLoading = ref(false);
  const filterDateRang = ref<[string, string]>([
    dayjs().day(-6).format('YYYY-MM-DD HH:mm:ss'),
    dayjs().format('YYYY-MM-DD HH:mm:ss'),
  ]);

  const logState = reactive({
    data: {} as TableItem,
    isShow: false,
    title: '',
  });
  const tableData = shallowRef<TableItem[]>([]);

  const columns = [
    {
      field: 'bk_biz_name',
      fixed: 'left',
      label: t('业务'),
      minWidth: 100,
    },
    {
      field: 'cluster',
      fixed: 'left',
      label: t('集群域名'),
      minWidth: 300,
      render: ({ data }: { data: TableItem }) => (
        <bk-button
          theme='primary'
          text
          onClick={() => handleToCluster(data)}>
          {data.cluster}
        </bk-button>
      ),
    },
    {
      field: 'db_type',
      label: t('实例类型'),
      minWidth: 100,
    },
    {
      field: 'db_role',
      label: t('实例角色'),
      minWidth: 100,
      render: ({ cell }: { cell: string }) => cell || '--',
    },
    {
      field: 'ip',
      label: t('故障IP'),
      minWidth: 100,
    },
    {
      field: 'port',
      label: t('故障Port'),
      minWidth: 100,
    },
    {
      field: 'slave_ip',
      label: t('新IP'),
      minWidth: 150,
      render: ({ cell }: { cell: string }) => cell || '--',
    },
    {
      field: 'slave_port',
      label: t('新Port'),
      minWidth: 150,
    },
    {
      field: 'switch_start_time',
      label: t('开始时间'),
      render: ({ cell }: { cell: string }) => utcDisplayTime(cell) || '--',
      width: 250,
    },
    {
      field: 'switch_finished_time',
      label: t('结束时间'),
      render: ({ cell }: { cell: string }) => utcDisplayTime(cell) || '--',
      width: 250,
    },
    {
      field: 'cost_time',
      label: t('耗时'),
      minWidth: 150,
    },
    {
      field: 'switch_result',
      label: t('切换结果'),
      minWidth: 150,
      render: ({ cell, data }: { cell: string; data: TableItem }) => {
        if (['failed', 'success'].includes(cell)) {
          return <DbStatus theme={data.result_info.theme}>{data.result_info.text}</DbStatus>;
        }

        return cell || '--';
      },
    },
    {
      field: 'confirm_result',
      label: t('切换原因'),
      minWidth: 200,
      showOverflowTooltip: {
        popoverOption: {
          maxWidth: 300,
        },
      },
    },
    {
      field: '',
      fixed: 'right',
      label: t('操作'),
      render: ({ data }: { data: TableItem }) => (
        <bk-button
          theme='primary'
          text
          onClick={() => handleShowDetails(data)}>
          {t('详情')}
        </bk-button>
      ),
      width: 100,
    },
  ];

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: columns.map((item) => item.field).filter((key) => !!key) as string[],
    fields: columns
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['bk_biz_name', 'cluster', 'ip', 'port', 'slave_ip', 'slave_port'].includes(item.field as string),
        field: item.field as string,
        label: item.label as string,
      })),
  };
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.DBHA_SWITCH_EVENTS, defaultSettings);

  const fetchTableData = () => {
    isLoading.value = true;
    const timeArr = filterDateRang.value;
    getEventSwitchList(
      {
        app: window.PROJECT_CONFIG.BIZ_ID,
        switch_finished_time: timeArr[1] ? dayjs(timeArr[1]).format('YYYY-MM-DD HH:mm:ss') : '',
        switch_start_time: timeArr[0] ? dayjs(timeArr[0]).format('YYYY-MM-DD HH:mm:ss') : '',
      },
      {
        permission: 'page',
      },
    )
      .then((res) => {
        isAnomalies.value = false;
        tableData.value = res.map((item) => {
          let costTime = '--';
          if (item.switch_start_time && item.switch_finished_time) {
            const endTime = dayjs(item.switch_finished_time).valueOf();
            const startTime = dayjs(item.switch_start_time).valueOf();
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
    } else if (['PredixyTendisplusCluster', 'TwemproxyRedisInstance'].includes(clusterType)) {
      routeName = 'RedisManage';
    } else if (clusterType === 'es') {
      routeName = 'EsManage';
    } else if (clusterType === 'hdfs') {
      routeName = 'HdfsManage';
    } else if (clusterType === 'kafka') {
      routeName = 'KafkaManage';
    }

    router.push({
      name: routeName,
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
