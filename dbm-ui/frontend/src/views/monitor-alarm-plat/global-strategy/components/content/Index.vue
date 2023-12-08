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
      :placeholder="t('请选择条件搜索')"
      unique-select
      value-split-code="+"
      @search="fetchHostNodes" />
    <BkLoading :loading="isTableLoading">
      <DbTable
        ref="tableRef"
        class="table-box"
        :columns="columns"
        :data-source="queryMonitorPolicyList"
        :row-class="updateRowClass"
        :settings="settings"
        @clear-search="handleClearSearch" />
    </BkLoading>
  </div>
  <EditRule
    v-model="isShowEditStrrategySideSilder"
    :data="currentChoosedRow"
    @success="handleEditRuleSuccess" />
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    disablePolicy,
    enablePolicy,
    queryMonitorPolicyList,
  } from '@services/monitor';

  import MiniTag from '@components/mini-tag/index.vue';

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

  const tableRef = ref();
  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as RowData);
  const isTableLoading = ref(false);

  async function fetchHostNodes() {
    isTableLoading.value = true;
    try {
      await tableRef.value.fetchData({ ...reqParams.value }, {
        bk_biz_id: 0,
        db_type: props.activeDbType,
      });
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
    return {
      ...searchParams,
    };
  });

  const searchSelectList = computed(() => ([
    {
      name: t('策略名称'),
      id: 'name',
    },
    {
      name: t('更新人'),
      id: 'updater',
    },
  ]));

  const columns = [
    {
      label: t('策略名称'),
      field: 'name',
      fixed: 'left',
      minWidth: 150,
      render: ({ row }: { row: RowData }) => {
        const isNew = dayjs().isBefore(dayjs(row.create_at).add(24, 'hour'));
        return (<span>
          <bk-button
            text
            theme="primary"
            onClick={() => handleEdit(row)}>
            {row.name}
          </bk-button>
          {isNew && <MiniTag theme='success' content="NEW" />}
        </span>);
      },
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
      width: 130,
      render: () => (
        <span class="notify-box">
          <db-icon type="yonghuzu" style="font-size: 16px;color: #979BA5" />
          <span class="dba">{t('业务 DBA')}</span>
        </span>),
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      width: 180,
    },
    {
      label: t('更新人'),
      field: 'updater',
      showOverflowTooltip: true,
      width: 150,
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
        <bk-switcher
          v-model={row.is_enabled}
          size="small"
          theme="primary"
          onChange={() => handleChangeSwitch(row)} />
      </bk-pop-confirm>
    ),
    },
    {
      label: t('操作'),
      fixed: 'right',
      showOverflowTooltip: false,
      field: '',
      width: 120,
      render: ({ row }: { row: RowData }) => (
      <div class="operate-box">
        <bk-button
          text
          theme="primary"
          onClick={() => handleEdit(row)}>
          {t('编辑')}
        </bk-button>
      </div>),
    },
  ];

  const settings = {
    fields: [
      {
        label: t('策略名称'),
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
    setTimeout(() => {
      fetchHostNodes();
    });
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => props.activeDbType, (type) => {
    if (type) {
      setTimeout(() => {
        fetchHostNodes();
      });
    }
  }, {
    immediate: true,
  });

  const updateRowClass = (row: RowData) => (dayjs().isBefore(dayjs(row.create_at).add(24, 'hour')) ? 'is-new' : '');

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
      runEnablePolicy({ id: row.id });
    }
  };

  const handleClickConfirm = (row: RowData) => {
    runDisablePolicy({ id: row.id });
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

  const handleEditRuleSuccess = () => {
    fetchHostNodes();
    window.changeConfirm = false;
  };

  const handleClearSearch = () => {
    searchValue.value = [];
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

  :deep(.table-box) {
    .strategy-title {
      display: flex;

      .name {
        margin-left: 8px;
      }
    }

    .notify-box {
      display: inline-block;
      height: 22px;
      padding: 2.5px 5px;
      background: #F0F1F5;
      border-radius: 2px;

      .dba {
        margin-left: 8px;
      }
    }

    .operate-box {
      display: flex;
      align-items: center;
    }

    .is-new {
      td {
        background-color: #f3fcf5 !important;
      }
    }
  }

}
</style>
