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
  <div class="type-content-box">
    <div class="create-box">
      <BkButton
        class="w-88 mb-14"
        theme="primary"
        @click="handleClickCreateNew">
        {{ t('新建') }}
      </BkButton>
    </div>
    <DbOriginalTable
      class="table-box"
      :columns="columns"
      :data="tableData"
      :pagination="pagination"
      remote-pagination
      :settings="settings"
      @page-limit-change="handeChangeLimit"
      @page-value-change="handleChangePage"
      @refresh="fetchHostNodes" />
  </div>
  <EditRule v-model="isShowEditRuleSideSilder" />
</template>
<script lang="tsx">
  import { queryDutyRuleList } from '@services/monitor';

  export type RowData = ServiceReturnType<typeof queryDutyRuleList>['results'][0];
</script>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import NumberInput from '@components/tools-table-input/index.vue';

  import EditRule from './edit-rule/Index.vue';
  import RenderRotateTable from './RenderRotateTable.vue';

  interface Props {
    activeDbType: string;
  }

  const props = defineProps<Props>();

  enum RuleStatus {
    TERMINATED = 'TERMINATED', // 已停用
    EXPIRED = 'EXPIRED', // 已失效
    NOT_ACTIVE = 'NOT_ACTIVE', // 未生效
    ACTIVE = 'ACTIVE', // 当前生效
  }

  const { t } = useI18n();

  const isShowEditRuleSideSilder = ref(false);
  const pagination = ref({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const tableData = ref<RowData[]>([
    {
      id: 1,
      creator: 'admin',
      create_at: '2023-09-21 21:49:46',
      updater: 'admin',
      update_at: '2023-09-21 21:49:46',
      name: '周末轮值',
      priority: 1,
      is_enabled: true,
      effective_time: '2023-09-05 00:00:00',
      end_time: '',
      category: 'handoff',
      db_type: 'mysql',
      duty_arranges: [
        {
          members: [
            'admin',
          ],
          duty_day: 1,
          work_days: [
            6,
            7,
          ],
          work_type: 'daily',
          work_times: [
            '00:00--11:59',
            '12:00--23:59',
          ],
          duty_number: 2,
        },
      ],
      is_show_edit: false,
    },
    {
      id: 2,
      creator: 'admin',
      create_at: '2023-09-21 21:50:41',
      updater: 'admin',
      update_at: '2023-09-21 21:50:41',
      name: '固定排班',
      priority: 2,
      is_enabled: true,
      effective_time: '2023-10-01 00:00:00',
      end_time: '2023-10-03 00:00:00',
      category: 'regular',
      db_type: 'redis',
      duty_arranges: [
        {
          date: '2023-10-01',
          members: [
            'admin',
          ],
          work_times: [
            '00:00--11:59',
            '12:00--23:59',
          ],
        },
        {
          date: '2023-10-02',
          members: [
            'admin',
          ],
          work_times: [
            '08:00--18:00',
          ],
        },
        {
          date: '2023-10-03',
          members: [
            'admin',
          ],
          work_times: [
            '00:00--11:59',
            '12:00--23:59',
          ],
        },
      ],
      is_show_edit: false,
    },
  ]);

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
        const { label, theme } = statusMap[RuleStatus.ACTIVE];
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
        const title = '';
        // if (row.status === RuleStatus.ACTIVE) {
        //   title = t('当前值班人');
        // } else if (row.status === RuleStatus.NOT_ACTIVE) {
        //   title = t('待值班人');
        // } else {
        //   return <div class="display-text" style="width: 27px;">--</div>;
        // }
        return (
          <div class="rotate-table-column">
            <bk-popover placement="bottom" theme="light" width={780}>
              {{
                default: () => (
                  <div class="display-text">{title}：</div>
                ),
                content: () => <RenderRotateTable />,
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
      showOverflowTooltip: true,
      width: 120,
      render: ({ row }: {row: RowData}) => <bk-switcher v-model={row.is_enabled} theme="primary" onChange={handleChangeSwitch}/>,
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ row }: {row: RowData}) => (
      <div class="operate-box">
        <span onClick={handleEdit}>{t('编辑')}</span>
        <span onClick={handleClone}>{t('克隆')}</span>
        {!row.is_enabled && <span onClick={handleDelete}>{t('删除')}</span>}
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
    const ret = await queryDutyRuleList({
      db_type: props.activeDbType,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    });
    console.log('>>>>', ret);
    // tableData.value = ret.results;
    pagination.value.count = ret.count;
  };

  const handleClickCreateNew = () => {
    isShowEditRuleSideSilder.value = true;
  };

  const handleClickEditPriority = (data: RowData) => {
    Object.assign(data, {
      isShowEdit: true,
    });
  };

  const handlePriorityChange = (row: RowData, value: string) => {
    Object.assign(row, {
      priority: Number(value),
      isShowEdit: false,
    });
  };

  const handleChangeSwitch = (status: boolean) => {
    console.log('isOpen: ', status);
  };

  const handleEdit = () => {
    console.log(tableData.value);
  };

  const handleClone = () => {
    console.log(tableData.value);
  };

  const handleDelete = () => {
    console.log(tableData.value);
  };
</script>
<style lang="less" scoped>
.type-content-box {
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
