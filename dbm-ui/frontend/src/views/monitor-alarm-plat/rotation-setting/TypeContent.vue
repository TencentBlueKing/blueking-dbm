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
      :settings="settings" />
  </div>
  <EditRule v-model="isShowEditRuleSideSilder" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import NumberInput from '@components/tools-table-input/index.vue';

  import EditRule from './edit-rule/Index.vue';
  import RenderRotateTable from './RenderRotateTable.vue';

  enum RuleStatus {
    TERMINATED = 'TERMINATED', // 已停用
    EXPIRED = 'EXPIRED', // 已失效
    NOT_ACTIVE = 'NOT_ACTIVE', // 未生效
    ACTIVE = 'ACTIVE', // 当前生效
  }

  interface RowData {
    ruleName: string,
    status: RuleStatus,
    priority: number,
    rotateTable: string,
    effectiveTime: string,
    updateTime: string,
    updator: string,
    isStart: boolean,
    isShowEdit: boolean,
  }

  const { t } = useI18n();

  const isShowEditRuleSideSilder = ref(false);

  const tableData = ref<RowData[]>([
    {
      ruleName: '夜间轮值',
      status: RuleStatus.ACTIVE,
      priority: 12,
      rotateTable: 'string',
      effectiveTime: '2023-12-12 ～2023-12-30',
      updateTime: '2021-10-15 13:21:43',
      updator: 'admin',
      isStart: true,
      isShowEdit: false,
    },
    {
      ruleName: '五一轮值',
      status: RuleStatus.NOT_ACTIVE,
      priority: 8,
      rotateTable: 'string',
      effectiveTime: '2023-12-12 ～2023-12-30',
      updateTime: '2021-10-15 13:21:43',
      updator: 'admin',
      isStart: true,
      isShowEdit: false,
    },
    {
      ruleName: '国庆轮值',
      status: RuleStatus.TERMINATED,
      priority: 3,
      rotateTable: 'string',
      effectiveTime: '2023-12-12 ～2023-12-30',
      updateTime: '2021-10-15 13:21:43',
      updator: 'admin',
      isStart: true,
      isShowEdit: false,
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

  const renderRuleName  = (row: RowData) => {
    const isNotActive = row.status === RuleStatus.TERMINATED || row.status === RuleStatus.EXPIRED;
    const color = isNotActive ? '#63656E' : '#3A84FF';
    return <span style={{ color, cursor: 'pointer' }}>{row.ruleName}</span>;
  };

  const renderStatus = (row: RowData) => {
    const { label, theme } = statusMap[row.status];
    return <bk-tag theme={theme}>{label}</bk-tag>;
  };

  const renderPriority = (row: RowData) => {
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
        !row.isShowEdit ? <>
        {!theme ? <bk-tag>{level}</bk-tag> : <bk-tag theme={theme} type="filled">{level}</bk-tag>}
        <db-icon class="edit-icon" type="edit" style="font-size: 18px"onClick={() => handleClickEditPriority(row)} />
        </> : <NumberInput type='number' placeholder={t('请输入 1～100 的数值')} onSubmit={(value: string) => handlePriorityChange(row, value)}/>
      }
    </div>);
  };

  const renderRotateTable = (row: RowData) => {
    let title = '';
    if (row.status === RuleStatus.ACTIVE) {
      title = t('当前值班人');
    } else if (row.status === RuleStatus.NOT_ACTIVE) {
      title = t('待值班人');
    } else {
      return <div class="display-text" style="width: 27px;">--</div>;
    }
    return <div class="rotate-table-column">
      <bk-popover placement="bottom" theme="light" width={780}>
            {{
              default: () => (
                <div class="display-text">{title}：</div>
              ),
              content: () => <RenderRotateTable />,
            }}
      </bk-popover>

    </div>;
  };
  const columns = [
    {
      label: t('规则名称'),
      field: 'ruleName',
      minWidth: 220,
      render: ({ data }: {data: RowData}) => renderRuleName(data),
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 220,
      render: ({ data }: {data: RowData}) => renderStatus(data),
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
      render: ({ data }: {data: RowData}) => renderPriority(data),
    },
    {
      label: t('轮值表'),
      field: 'rotateTable',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: RowData}) => renderRotateTable(data),
    },
    {
      label: t('生效时间'),
      field: 'effectiveTime',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('更新时间'),
      field: 'updateTime',
      showOverflowTooltip: true,
      sort: true,
      width: 120,
    },
    {
      label: t('更新人'),
      field: 'updator',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('启停'),
      field: 'isStart',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: {data: RowData}) => <bk-switcher v-model={data.isStart} theme="primary" onChange={handleChangeSwitch}/>,
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ data }: {data: RowData}) => (
      <div class="operate-box">
        <span onClick={handleEdit}>{t('编辑')}</span>
        <span onClick={handleClone}>{t('克隆')}</span>
        {!data.isStart && <span onClick={handleDelete}>{t('删除')}</span>}
      </div>),
    },
  ];

  const settings = {
    fields: [
      {
        label: t('规则名称'),
        field: 'ruleName',
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
        field: 'rotateTable',
      },
      {
        label: t('生效时间'),
        field: 'effectiveTime',
      },
      {
        label: t('更新时间'),
        field: 'updateTime',
      },
      {
        label: t('更新人'),
        field: 'updator',
      },
      {
        label: t('启停'),
        field: 'isStart',
      },
    ],
    checked: ['ruleName', 'status', 'priority', 'rotateTable', 'effectiveTime', 'updateTime', 'updator', 'isStart'],
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
