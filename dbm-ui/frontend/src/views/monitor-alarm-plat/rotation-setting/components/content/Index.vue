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
  <div class="rotation-setting-type-content">
    <div class="create-box">
      <BkButton
        class="w-88 mb-14"
        theme="primary"
        @click="handleClickCreateNew">
        {{ t('新建') }}
      </BkButton>
    </div>
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
    v-model="isShowEditRuleSideSilder"
    :data="currentRowData"
    :db-type="activeDbType"
    :page-type="pageType"
    @success="handleSuccess" />
</template>
<script lang="tsx">
  import {
    deleteDutyRule,
    queryDutyRuleList,
    updatePartialDutyRule,
  } from '@services/monitor';

  export type RowData = ServiceReturnType<typeof queryDutyRuleList>['results'][0];
</script>
<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import NumberInput from '@components/tools-table-input/index.vue';

  import EditRule from '../edit-rule/Index.vue';

  import RenderRotateTable from './RenderRotateTable.vue';

  interface Props {
    activeDbType: string;
  }

  const props = defineProps<Props>();

  const enum RuleStatus {
    TERMINATED = 'TERMINATED', // 已停用
    EXPIRED = 'EXPIRED', // 已失效
    NOT_ACTIVE = 'NOT_ACTIVE', // 未生效
    ACTIVE = 'ACTIVE', // 当前生效
  }

  const { t } = useI18n();

  const pageType = ref();
  const isShowEditRuleSideSilder = ref(false);
  const currentRowData = ref<RowData>();
  const pagination = ref({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const tableData = ref<RowData[]>([]);
  const isTableLoading = ref(false);

  const statusMap = {
    [RuleStatus.ACTIVE]: {
      label: t('当前生效'),
      theme: 'success',
    },
    [RuleStatus.NOT_ACTIVE]: {
      label: t('未生效'),
      theme: 'info',
    },
    [RuleStatus.EXPIRED]: {
      label: t('已失效'),
      theme: '',
    },
    [RuleStatus.TERMINATED]: {
      label: t('已停用'),
      theme: '',
    },
  };

  const columns = [
    {
      label: t('规则名称'),
      field: 'name',
      minWidth: 220,
      render: ({ row }: {row: RowData}) => {
        const isNotActive = true; // row.status === RuleStatus.TERMINATED || row.status === RuleStatus.EXPIRED;
        const color = isNotActive ? '#63656E' : '#3A84FF';
        return <span style={{ color, cursor: 'pointer' }}>{row.name}</span>;
      },
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 220,
      render: ({ row }: {row: RowData}) => {
        const { label, theme } = statusMap[row.status as RuleStatus];
        return <bk-tag theme={theme}>{label}</bk-tag>;
      },
    },
    {
      label: () => <div v-bk-tooltips={
        {
          content: t('范围 1～100，数字越高代表优先级越高，当有规则冲突时，优先执行数字较高的规则'),
          theme: 'dark',
        }} style="border-bottom: 1px dashed #979BA5;">{t('优先级')}</div>,
      field: 'priority',
      sort: true,
      width: 120,
      render: ({ row }: {row: RowData}) => {
        const level = row.priority;
        let theme = 'success';
        if (level >= 10) {
          theme = 'danger';
        } else if (level === 9) {
          theme = 'warning';
        } else if (level === 8) {
          theme = 'success';
        } else {
          theme = '';
        }
        return (
          <div class="priority-box">
            {
              !row.is_show_edit ? <>
              {!theme ? <bk-tag>{level}</bk-tag> : <bk-tag theme={theme} type="filled">{level}</bk-tag>}
              <db-icon class="edit-icon" type="edit" style="font-size: 18px"onClick={() => handleClickEditPriority(row)} />
              </> : <NumberInput type='number' placeholder={t('请输入 1～100 的数值')} onSubmit={(value: string) => handlePriorityChange(row, value)}/>
            }
          </div>
        );
      },
    },
    {
      label: t('轮值表'),
      field: 'duty_arranges',
      showOverflowTooltip: true,
      width: 250,
      render: ({ row }: {row: RowData}) => {
        let title = '';
        if (row.status === RuleStatus.ACTIVE) {
          title = t('当前值班人');
        } else if (row.status === RuleStatus.NOT_ACTIVE) {
          title = t('待值班人');
        } else {
          return <div class="display-text" style="width: 27px;">--</div>;
        }
        const peoples = row.duty_arranges.map(item => item.members.join(',')).join(',');
        return (
          <div class="rotate-table-column">
            <bk-popover placement="bottom" theme="light" width={780} popoverDelay={0}>
              {{
                default: () => (
                  <div class="display-text">{title}: {peoples}</div>
                ),
                content: () => <RenderRotateTable data={row} />,
              }}
            </bk-popover>
          </div>
        );
      },
    },
    {
      label: t('生效时间'),
      field: 'effective_time',
      showOverflowTooltip: true,
      width: 180,
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
        <bk-switcher v-model={row.is_enabled} theme="primary" onChange={() => handleChangeSwitch(row)} />
      </bk-pop-confirm>
    ),
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ row }: {row: RowData}) => (
      <div class="operate-box">
        <span onClick={() => handleEdit(row)}>{t('编辑')}</span>
        <span onClick={() => handleClone(row)}>{t('克隆')}</span>
        {!row.is_enabled && <span onClick={() => handleDelete(row)}>{t('删除')}</span>}
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
        label: t('状态'),
        field: 'status',
      },
      {
        label: t('优先级'),
        field: 'priority',
      },
      {
        label: t('轮值表'),
        field: 'duty_arranges',
      },
      {
        label: t('生效时间'),
        field: 'effective_time',
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
    checked: ['name', 'status', 'priority', 'duty_arranges', 'effective_time', 'update_at', 'updater', 'is_enabled'],
  };

  watch(() => props.activeDbType, (type) => {
    if (type) {
      setTimeout(() => {
        fetchHostNodes();
      });
    }
  }, {
    immediate: true,
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
    isTableLoading.value = true;
    const ret = await queryDutyRuleList({
      db_type: props.activeDbType,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    }).finally(() => {
      isTableLoading.value = false;
    });
    tableData.value = ret.results;
    pagination.value.count = ret.count;
  };

  const handleClickCreateNew = () => {
    pageType.value = 'create';
    isShowEditRuleSideSilder.value = true;
  };

  const handleClickEditPriority = (data: RowData) => {
    Object.assign(data, {
      is_show_edit: true,
    });
  };

  const handlePriorityChange = async (row: RowData, value: string) => {
    const priority = Number(value);
    const updateResult = await updatePartialDutyRule(row.id, {
      priority,
    });
    if (updateResult.priority === priority) {
      // 设置成功
      Message({
        message: t('优先级设置成功'),
        theme: 'success',
      });
    }
    fetchHostNodes();
  };

  const handleChangeSwitch = async (row: RowData) => {
    if (!row.is_enabled) {
      nextTick(() => {
        Object.assign(row, {
          is_show_tip: true,
          is_enabled: !row.is_enabled,
        });
      });
    } else {
      // 启用
      const updateResult = await updatePartialDutyRule(row.id, {
        is_enabled: true,
      });
      if (updateResult.is_enabled) {
        Message({
          message: t('启用成功'),
          theme: 'success',
        });
      }
      fetchHostNodes();
    }
  };

  const handleClickConfirm = async (row: RowData) => {
    const updateResult = await updatePartialDutyRule(row.id, {
      is_enabled: false,
    });
    if (!updateResult.is_enabled) {
      // 停用成功
      Message({
        message: t('停用成功'),
        theme: 'success',
      });
    }
    fetchHostNodes();
  };

  const handleCancelConfirm = (row: RowData) => {
    Object.assign(row, {
      is_show_tip: false,
    });
  };

  const handleEdit = (row: RowData) => {
    currentRowData.value = row;
    pageType.value = 'edit';
    isShowEditRuleSideSilder.value = true;
  };

  const handleClone = (row: RowData) => {
    currentRowData.value = row;
    pageType.value = 'clone';
    isShowEditRuleSideSilder.value = true;
  };

  const handleDelete = async (row: RowData) => {
    await deleteDutyRule(row.id);
    fetchHostNodes();
  };

  const handleSuccess = () => {
    fetchHostNodes();
  };
</script>
<style lang="less" scoped>
.rotation-setting-type-content {
  display: flex;
  flex-direction: column;

  .create-box {
    width: 100%;
  }

  .table-box {
    :deep(.priority-box) {
      display: flex;
      align-items: center;

      &:hover {
        .edit-icon {
          display: block;
        }
      }

      .edit-icon {
        display: none;
        color: #3A84FF;
        cursor: pointer;
      }
    }

    :deep(.display-text) {
      height: 22px;
      padding: 0 8px;
      overflow: hidden;
      line-height: 22px;
      color: #63656E;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
      background: #F0F1F5;
      border-radius: 2px;
    }

    // :deep(.rotate-table-column) {
    // }

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
