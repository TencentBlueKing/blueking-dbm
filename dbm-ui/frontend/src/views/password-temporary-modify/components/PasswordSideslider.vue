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
  <BkSideslider
    :is-show="isShow"
    :title="t('临时密码生效的实例')"
    :width="1200"
    @closed="isShow = false;">
    <div class="password-sideslider">
      <div class="operate-area">
        <BkButton
          :disabled="!selectionLength"
          @click="handleInstancesCopy">
          {{ t('复制实例') }}
        </BkButton>
        <BkDatePicker
          v-model="searchParams.time"
          class="ml-8"
          clearable
          format="yyyy-MM-dd HH:mm:ss"
          :placeholder="t('请选择')"
          type="datetimerange"
          @change="getDataSource"
          @clear="getDataSource" />
        <DbSearchSelect
          v-model="searchParams.keys"
          class="ml-8 search-select"
          :data="searchSelectData"
          :placeholder="t('请输入实例搜索')"
          @change="getDataSource" />
      </div>
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="queryMysqlAdminPassword"
        :max-height="tableMaxHeight"
        :pagination-extra="{
          small: true
        }"
        row-class="password-sideslider-table-row"
        show-overflow-tooltip
        @clear-search="getDataSource"
        @selection-change="handleSelectionChange" />
    </div>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import { queryMysqlAdminPassword } from '@services/permission';

  import {
    useCopy,
    useTableMaxHeight,
  } from '@hooks';

  import { OccupiedInnerHeight } from '@common/const';

  import { getSearchSelectorParams } from '@utils';

  interface TableRow {
    row: ServiceReturnType<typeof queryMysqlAdminPassword>['results'][number] & {
      passwordShow: boolean
    }
  }

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const copy = useCopy();
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);

  const searchSelectData = [
    {
      name: t('实例'),
      id: 'instances',
      placeholder: `${t('请输入实例搜索')}(eg: 127.0.0.1:8000)`,
    },
  ];

  const columns = [
    {
      type: 'selection',
      width: 48,
    },
    {
      label: t('云区域'),
      field: 'bk_cloud_name',
      width: 100,
    },
    {
      label: t('实例'),
      field: 'instance',
      width: 150,
      render: ({ row }: TableRow) => {
        const instance = `${row.ip}:${String(row.port)}`;
        return (
          <>
            <span>{ instance }</span>
            <bk-button
              text
              theme="primary"
              onClick={ () => handleCopy(instance) }>
              <db-icon type="copy row-copy-icon ml-4"/>
            </bk-button>
          </>
        );
      },
    },
    {
      label: () => (
        <>
          <span>{ t('密码') }</span>
          <bk-button
            text
            onClick={ () => handlePasswordShow() }>
            <db-icon type="visible1 ml-4"/>
          </bk-button>
        </>
      ),
      field: 'password',
      width: 200,
      showOverflowTooltip: true,
      render: ({ row }: TableRow) => (
        <>
          <span>
            {
              row.passwordShow
                ? row.password
                : '*'.repeat(row.password.length)
            }
            </span>
          <bk-button
            text
            theme="primary"
            onClick={ () => handleCopy(row.password) }>
            <db-icon type="copy row-copy-icon ml-4"/>
          </bk-button>
        </>
      ),
    },
    {
      label: t('DB类型'),
      field: 'component',
      width: 100,
      render: ({ row }: TableRow) => (
        <>
          <db-icon type="mysql row-type"/>
          <span class='ml-4'>{ row.component }</span>
        </>
      ),
    },
    {
      label: t('过期时间'),
      field: 'lock_until',
      minWidth: 240,
      sort: true,
      showOverflowTooltip: true,
      render: ({ row }: TableRow) => {
        const { lock_until: lockUntil } = row;
        const lockUntilDate = dayjs(lockUntil).format('YYYY-MM-DD');
        const currentDate = dayjs().format('YYYY-MM-DD');
        const diffDay = dayjs(lockUntilDate).diff(currentDate, 'day');

        return diffDay <= 7
          ? <span
              class='expired-time'>
              { lockUntil }（{ t('n天后过期', [Math.ceil(diffDay)]) }）
            </span>
          : <span>{ lockUntil }</span>;
      },
    },
    {
      label: t('修改人'),
      field: 'operator',
      width: 150,
    },
    {
      label: t('修改时间'),
      field: 'update_time',
      width: 160,
      sort: true,
    },
  ];

  const tableRef = ref();
  const selectionLength = ref(0);
  const searchParams = reactive({
    time: ['', ''] as [string, string],
    keys: [],
  });

  watch(tableRef, (newVal) => {
    if (newVal) {
      getDataSource();
    }
  });

  const handlePasswordShow = () => {
    tableRef.value.getData().forEach((row: TableRow['row']) => Object.assign(row, { passwordShow: !row.passwordShow }));
  };

  const getDataSource = () => {
    const keys = getSearchSelectorParams(searchParams.keys);
    const params = {
      ...keys,
    };

    if (searchParams.time.length) {
      const [beginTime, endTime] = searchParams.time;

      if (beginTime && endTime) {
        Object.assign(params, {
          begin_time: dayjs(beginTime).format('YYYY-MM-DD HH:mm:ss'),
          end_time: dayjs(endTime).format('YYYY-MM-DD HH:mm:ss'),
        });
      }
    }

    tableRef.value?.fetchData({}, params);
  };

  const handleSelectionChange = () => {
    selectionLength.value = tableRef.value?.bkTableRef.getSelection().length;
  };

  const handleInstancesCopy = () => {
    const instances = tableRef.value?.bkTableRef.getSelection().map((row: TableRow['row']) => `${row.ip}:${String(row.port)}`);
    copy(instances.join('\n'));
  };

  const handleCopy = (val: string) => {
    copy(val);
  };
</script>

<style lang="less" scoped>
.password-sideslider {
  padding: 16px 24px;

  .operate-area {
    display: flex;
    margin-bottom: 16px;

    .search-select {
      flex: 1;
    }
  }

  :deep(.row-copy-icon) {
    display: none;
  }

  :deep(.password-sideslider-table-row) {
    &:hover {
      .row-copy-icon {
        display: inline;
      }
    }
  }

  :deep(.row-type) {
    font-size: 16px;
  }

  :deep(.expired-time) {
    color: @warning-color;
  }
}
</style>
