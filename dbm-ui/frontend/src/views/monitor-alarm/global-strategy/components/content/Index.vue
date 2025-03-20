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
  <ApplyPermissionCatch>
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
          :data-source="dataSource"
          :row-class="updateRowClass"
          @clear-search="handleClearSearch" />
      </BkLoading>
    </div>
    <EditStrategy
      v-model="isShowEditStrrategySideSilder"
      :data="currentChoosedRow"
      @success="handleEditRuleSuccess" />
  </ApplyPermissionCatch>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { disablePolicy, enablePolicy, queryMonitorPolicyList } from '@services/source/monitor';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import MiniTag from '@components/mini-tag/index.vue';

  import { messageSuccess } from '@utils';

  import EditStrategy from '../edit-strategy/Index.vue';

  interface Props {
    activeDbType: string;
  }

  interface SearchSelectItem {
    id: string;
    name: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataSource = (params: ServiceParameters<typeof queryMonitorPolicyList>) =>
    queryMonitorPolicyList(
      Object.assign(params, {
        db_type: props.activeDbType,
      }),
      {
        permission: 'catch',
      },
    );

  const tableRef = ref();
  const searchValue = ref<Array<{ values: SearchSelectItem[] } & SearchSelectItem>>([]);
  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as MonitorPolicyModel);
  const isTableLoading = ref(false);
  const showTipMap = ref<Record<string, boolean>>({});

  async function fetchHostNodes() {
    isTableLoading.value = true;
    try {
      await tableRef.value.fetchData(
        { ...reqParams.value },
        {
          bk_biz_id: 0,
          db_type: props.activeDbType,
        },
      );
    } finally {
      isTableLoading.value = false;
    }
  }

  const reqParams = computed(() => {
    const searchParams = searchValue.value.reduce(
      (obj, item) => {
        Object.assign(obj, {
          [item.id]: item.values.map((data) => data.id).join(','),
        });
        return obj;
      },
      {} as Record<string, string>,
    );
    return {
      ...searchParams,
    };
  });

  const searchSelectList = [
    {
      id: 'name',
      name: t('策略名称'),
    },
    {
      id: 'updater',
      name: t('更新人'),
    },
  ];

  const columns = [
    {
      field: 'name',
      fixed: 'left',
      label: t('策略名称'),
      minWidth: 150,
      render: ({ data }: { data: MonitorPolicyModel }) => (
        <span>
          <auth-button
            action-id='global_monitor_policy_edit'
            permission={data.permission.global_monitor_policy_edit}
            resource={data.id}
            theme='primary'
            text
            onClick={() => handleEdit(data)}>
            {data.name}
          </auth-button>
          {data.isNewCreated && (
            <MiniTag
              content='NEW'
              theme='success'
            />
          )}
        </span>
      ),
    },
    {
      field: 'targets',
      label: t('监控目标'),
      render: () => <span>{t('全部业务')}</span>,
      width: 130,
    },
    {
      field: 'notify_groups',
      label: t('默认通知对象'),
      render: () => (
        <span class='notify-box'>
          <db-icon
            style='font-size: 16px;color: #979BA5'
            type='yonghuzu'
          />
          <span class='dba'>{t('业务 DBA')}</span>
        </span>
      ),
      showOverflowTooltip: true,
      width: 180,
    },
    {
      field: 'update_at',
      label: t('更新时间'),
      render: ({ data }: { data: MonitorPolicyModel }) => <span>{data.updateAtDisplay}</span>,
      showOverflowTooltip: true,
      sort: true,
      width: 220,
    },
    {
      field: 'updater',
      label: t('更新人'),
      render: ({ data }: { data: MonitorPolicyModel }) => <span>{data.updater || '--'}</span>,
      showOverflowTooltip: true,
      width: 150,
    },
    {
      field: 'is_enabled',
      label: t('启停'),
      render: ({ data }: { data: MonitorPolicyModel }) => (
        <bk-pop-confirm
          content={t('停用后，所有的业务将会停用该策略，请谨慎操作！')}
          is-show={showTipMap.value[data.id]}
          placement='bottom'
          title={t('确认停用该策略？')}
          trigger='manual'
          width='320'
          onCancel={() => handleCancelConfirm(data)}
          onConfirm={() => handleClickConfirm(data)}>
          <auth-switcher
            v-model={data.is_enabled}
            action-id='global_monitor_policy_start_stop'
            permission={data.permission.global_monitor_policy_start_stop}
            resource={data.id}
            size='small'
            theme='primary'
            onChange={() => handleChangeSwitch(data)}
          />
        </bk-pop-confirm>
      ),
      width: 120,
    },
    {
      field: '',
      fixed: 'right',
      label: t('操作'),
      render: ({ data }: { data: MonitorPolicyModel }) => (
        <auth-button
          action-id='global_monitor_policy_edit'
          permission={data.permission.global_monitor_policy_edit}
          resource={data.id}
          theme='primary'
          text
          onClick={() => handleEdit(data)}>
          {t('编辑')}
        </auth-button>
      ),
      showOverflowTooltip: false,
      width: 120,
    },
  ];

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

  watch(
    reqParams,
    () => {
      setTimeout(() => {
        if (tableRef.value) {
          fetchHostNodes();
        }
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const updateRowClass = (row: MonitorPolicyModel) => (row.isNewCreated ? 'is-new' : '');

  const handleChangeSwitch = (row: MonitorPolicyModel) => {
    if (!row.is_enabled) {
      showTipMap.value[row.id] = true;
      Object.assign(row, {
        is_enabled: !row.is_enabled,
      });
    } else {
      // 启用
      runEnablePolicy({ id: row.id });
    }
  };

  const handleClickConfirm = (row: MonitorPolicyModel) => {
    runDisablePolicy({ id: row.id });
    showTipMap.value[row.id] = false;
  };

  const handleCancelConfirm = (row: MonitorPolicyModel) => {
    showTipMap.value[row.id] = false;
  };

  const handleEdit = (row: MonitorPolicyModel) => {
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
        background: #f0f1f5;
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
