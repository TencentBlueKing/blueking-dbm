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
  <div class="global-strategy-type-content">
    <BkSearchSelect
      v-model="searchValue"
      class="input-box"
      :data="searchSelectList"
      :placeholder="t('请输入策略关键字或选择条件搜索')"
      unique-select
      value-split-code="+"
      @search="fetchHostNodes" />
    <BkLoading :loading="isTableLoading">
      <DbOriginalTable
        class="table-box"
        :columns="columns"
        :data="tableData"
        :pagination="pagination.count > 10 ? pagination : false"
        remote-pagination
        :settings="settings"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchHostNodes" />
    </BkLoading>
  </div>
  <EditRule
    v-model="isShowEditStrrategySideSilder"
    :data="currentChoosedRow"
    @success="fetchHostNodes" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    disablePolicy,
    enablePolicy,
    getAlarmGroupList,
    queryMonitorPolicyList,
  } from '@services/monitor';

  import { useDefaultPagination } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageSuccess } from '@utils';

  import EditRule from '../edit-strategy/Index.vue';

  export type RowData = ServiceReturnType<typeof queryMonitorPolicyList>['results'][0];

  interface Props {
    activeDbType: string;
  }

  interface SearchSelectItem {
    id: string,
    name: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as RowData);
  const alarmGroupList = ref<SelectItem<string>[]>([]);
  const tableData = ref<RowData[]>([]);
  const pagination = ref({
    ...useDefaultPagination(),
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const isTableLoading = ref(false);

  async function fetchHostNodes() {
    isTableLoading.value = true;
    try {
      const result = await queryMonitorPolicyList(reqParams.value);
      tableData.value = result.results;
      pagination.value.count = result.count;
    } finally {
      isTableLoading.value = false;
    }
  }

  const reqParams = computed(() => {
    const searchParams = searchValue.value.reduce((obj, item) => {
      Object.assign(obj, {
        [item.id]: item.values.map(data => data.id).join(','),
      });
      return obj;
    }, {} as Record<string, string>);
    const commonParams = {
      bk_biz_id: 0,
      db_type: props.activeDbType,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    };
    return {
      ...searchParams,
      ...commonParams,
    };
  });

  const searchSelectList = computed(() => ([
    {
      name: t('策略名称'),
      id: 'name',
    },
    {
      name: t('监控目标'),
      id: 'target_keyword',
    },
    {
      name: t('告警组'),
      id: 'notify_groups',
      multiple: true,
      children: alarmGroupList.value.map(item => ({
        id: item.value,
        name: item.label,
      })) as SearchSelectItem[],
    },
    {
      name: t('更新人'),
      id: 'updater',
    },
  ]));

  const alarmGroupNameMap: Record<string, string> = {};

  const columns = [
    {
      label: t('策略名称'),
      field: 'name',
      minWidth: 150,
    },
    {
      label: t('监控目标'),
      field: 'targets',
      width: 130,
      render: () => <span>{t('全部业务')}</span>,
    },
    {
      label: t('默认通知对象'),
      field: 'notify_groups',
      showOverflowTooltip: true,
      width: 120,
      render: () => (
        <div class="notify-box">
          <db-icon type="auth" style="font-size: 16px" />
          <span class="dba">{t('业务 DBA')}</span>
        </div>),
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      minWidth: 180,
    },
    {
      label: t('更新人'),
      field: 'updater',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('启停'),
      field: 'is_enabled',
      width: 120,
      render: ({ row }: { row: RowData }) => (
      <bk-pop-confirm
        title={t('确认停用该策略？')}
        content={t('停用后，所有的业务将会停用该策略，请谨慎操作！')}
        width="320"
        is-show={row.is_show_tip}
        trigger="manual"
        placement="bottom"
        onConfirm={() => handleClickConfirm(row)}
        onCancel={() => handleCancelConfirm(row)}
      >
        <bk-switcher size="small" v-model={row.is_enabled} theme="primary" onChange={() => handleChangeSwitch(row)} />
      </bk-pop-confirm>
    ),
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ row }: { row: RowData }) => (
      <div class="operate-box">
        <span onClick={() => handleEdit(row)}>{t('编辑')}</span>
      </div>),
    },
  ];

  const settings = {
    fields: [
      {
        label: t('规则名称'),
        field: 'name',
      },
      {
        label: t('监控目标'),
        field: 'targets',
      },
      {
        label: t('默认通知对象'),
        field: 'notify_groups',
      },
      {
        label: t('更新时间'),
        field: 'update_at',
      },
      {
        label: t('更新人'),
        field: 'updater',
      },
      {
        label: t('启停'),
        field: 'is_enabled',
      },
    ],
    checked: ['name', 'targets', 'notify_groups', 'update_at', 'updater', 'is_enabled'],
  };

  const { run: fetchAlarmGroupList } = useRequest(getAlarmGroupList, {
    manual: true,
    onSuccess: (res) => {
      alarmGroupList.value = res.results.map((item) => {
        alarmGroupNameMap[item.id] = item.name;
        return ({
          label: item.name,
          value: String(item.id),
        });
      });
    },
  });

  const { run: runEnablePolicy } = useRequest(enablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (isEnabled) {
        messageSuccess(t('启用成功'));
        fetchHostNodes();
      }
    },
  });

  const { run: runDisablePolicy } = useRequest(disablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (!isEnabled) {
        // 停用成功
        messageSuccess(t('停用成功'));
        fetchHostNodes();
      }
    },
  });

  watch(reqParams, () => {
    fetchHostNodes();
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => props.activeDbType, (type) => {
    if (type) {
      pagination.value.current = 1;
      pagination.value.limit = 10;
      setTimeout(() => {
        fetchAlarmGroupList({
          bk_biz_id: currentBizId,
          dbtype: type,
        });
      });
    }
  }, {
    immediate: true,
  });

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    pagination.value.current = 1;
  };

  const handleChangeSwitch = (row: RowData) => {
    if (!row.is_enabled) {
      nextTick(() => {
        Object.assign(row, {
          is_show_tip: true,
          is_enabled: !row.is_enabled,
        });
      });
    } else {
      // 启用
      runEnablePolicy(row.id);
    }
  };

  const handleClickConfirm = (row: RowData) => {
    runDisablePolicy(row.id);
  };

  const handleCancelConfirm = (row: RowData) => {
    Object.assign(row, {
      is_show_tip: false,
    });
  };

  const handleEdit = (row: RowData) => {
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

</script>
<style lang="less" scoped>
.global-strategy-type-content {
  display: flex;
  flex-direction: column;

  .input-box {
    width: 600px;
    height: 32px;
    margin-bottom: 16px;
  }

  .table-box {
    :deep(.strategy-title) {
      display: flex;

      .name {
        margin-left: 8px;
      }
    }

    :deep(.notify-box) {
      display: flex;
      width: 100%;
      height: 22px;
      padding: 2.5px 5px;
      background: #F0F1F5;
      border-radius: 2px;
      box-sizing: border-box;
      align-items: center;

      .dba {
        margin-left: 8px;
      }
    }

    :deep(.operate-box) {
      display: flex;
      gap: 15px;
      align-items: center;

      span {
        color: #3A84FF;
        cursor: pointer;
      }
    }
  }

}
</style>
