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
    <BkInput
      v-model="searchValue"
      class="input-box"
      :placeholder="t('请输入策略关键字或选择条件搜索')"
      size="default"
      type="search" />
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
  <EditRule
    v-model="isShowEditStrrategySideSilder"
    :data="currentChoosedRow" />
</template>
<script lang="tsx">
  import { queryMonitorPolicyList } from '@services/monitor';

  import RenderTargetItem from './RenderTargetItem.vue';
  // eslint-disable-next-line no-undef
  export type RowData = UnPromisify<typeof queryMonitorPolicyList>['results'][0];
</script>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import EditRule from '../edit-strategy/Index.vue';

  interface Props {
    activeDbType: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const searchValue = ref('');
  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as RowData);

  const tableData = ref<RowData[]>([]);

  const pagination = ref({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });

  const isSelectedAll = computed(() => {
    const checkedLen = tableData.value.filter(item => item.is_checked).length;
    const totalLen = tableData.value.length;
    return totalLen > 0 &&  checkedLen === totalLen;
  });

  const isIndeterminate = computed(() => {
    const checkedLen = tableData.value.filter(item => item.is_checked).length;
    const totalLen = tableData.value.length;
    return totalLen > 0 &&  checkedLen > 0 && checkedLen !== totalLen;
  });

  const renderMonitorTarget = (data: RowData) => (
      <div class="targets-box">
        {
          data.targets.map(item =>  <RenderTargetItem title={item.rule.key} list={item.rule.value}/>)
        }
      </div>
  );

  const columns = [
    {
      label: () => (
      <div class="strategy-title">
        <bk-checkbox
          indeterminate={isIndeterminate.value}
          model-value={isSelectedAll.value}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={handleSelectPageAll}
        />
        <span class="name">{t('策略名称')}</span>
      </div>
    ),
      field: 'name',
      minWidth: 150,
      render: ({ data }: { data: RowData }) => (
      <div class="strategy-title">
        <bk-checkbox
          model-value={data.is_checked}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={(value: boolean) => handleTableSelectOne(value, data)}
        />
        <span class="name" style="color:#3A84FF;">{data.name}</span>
      </div>
    ),
    },
    {
      label: t('监控目标'),
      field: 'targets',
      minWidth: 150,
      render: ({ data }: {data: RowData}) => renderMonitorTarget(data),
    },
    {
      label: t('默认通知对象'),
      field: 'notify_groups',
      showOverflowTooltip: true,
      width: 120,
      render: ({ data }: { data: RowData }) => (
      <div class="notify-box">
        <db-icon type="auth" style="font-size: 16px" />
        <span class="dba">{data.notify_groups.toString()}</span>
      </div>
    ),
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      width: 120,
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
      render: ({ data }: { data: RowData }) => (
      <bk-pop-confirm
        title={t('确认停用该策略？')}
        content={t('停用后，所有的业务将会停用该策略，请谨慎操作！')}
        width="320"
        is-show={data.is_show_tip}
        trigger="manual"
        placement="bottom"
        onConfirm={() => handleClickConfirm(data)}
        onCancel={() => handleCancelConfirm(data)}
      >
        <bk-switcher v-model={data.is_enabled} theme="primary" onChange={() => handleChangeSwitch(data)} />
      </bk-pop-confirm>
    ),
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ data }: { data: RowData }) => (
      <div class="operate-box">
        <span onClick={() => handleEdit(data)}>{t('编辑')}</span>
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
    const ret = await queryMonitorPolicyList({
      bk_biz_id: 0,
      db_type: props.activeDbType,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    });
    console.log('queryMonitorPolicyList>>>', ret);
    tableData.value = ret.results;
    pagination.value.count = ret.count;
  };


  const handleChangeSwitch = (row: RowData) => {
    if (!row.is_enabled) {
      nextTick(() => {
        Object.assign(row, {
          is_show_tip: true,
          is_enabled: !row.is_enabled,
        });
      });
    }
  };

  const handleSelectPageAll = (checked: boolean) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        is_checked: checked,
      });
    });
  };

  const handleTableSelectOne = (checked: boolean, data: RowData) => {
    Object.assign(data, {
      is_checked: checked,
    });
  };

  const handleClickConfirm = (row: RowData) => {
    Object.assign(row, {
      is_enabled: false,
      is_show_tip: false,
    });
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
.type-content-box {
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
