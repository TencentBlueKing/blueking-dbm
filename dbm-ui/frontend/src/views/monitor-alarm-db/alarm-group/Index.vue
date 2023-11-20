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
  <div class="alert-group">
    <div class="alert-group-operations mb-16">
      <BkButton
        theme="primary"
        @click="handleOpenDetail('add')">
        {{ t('新建') }}
      </BkButton>
      <BkInput
        v-model="keyword"
        class="search-input"
        clearable
        :placeholder="t('请输入告警组名称')"
        type="search"
        @clear="fetchTableData"
        @enter="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      class="alert-group-table"
      :columns="columns"
      :data-source="getAlarmGroupList"
      :row-class="setRowClass"
      @request-success="handleRequestSuccess" />
    <DetailDialog
      v-model="detailDialogShow"
      :biz-id="bizId"
      :detail-data="detailData"
      :name-list="nameList"
      :type="detailType"
      @successed="fetchTableData" />
  </div>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    deleteAlarmGroup,
    getAlarmGroupList,
    getUserGroupList,
  } from '@services/monitorAlarm';

  import { useInfoWithIcon } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import MiniTag from '@components/mini-tag/index.vue';
  import RenderTextEllipsisOneLine from '@components/text-ellipsis-one-line/index.vue';

  import { messageSuccess } from '@utils';

  import DetailDialog from './components/DetailDialog.vue';
  import RenderRow from './components/RenderRow.vue';

  import type { ListBase } from '@/services/types/common';

  const isNewUser = (createTime: string) => {
    if (!createTime) {
      return '';
    }

    const createDay = dayjs(createTime);
    const today = dayjs();
    return today.diff(createDay, 'hour') <= 24;
  };

  type AlarmGroupItem = ServiceReturnType<typeof getAlarmGroupList>['results'][number]

  interface TableRenderData {
    row: AlarmGroupItem
  }

  interface UserGroupMap {
    [key: string]: {
      id: string,
      displayName: string,
      type: string
    }
  }

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const route = useRoute();
  const router = useRouter();

  const isPlatform = route.matched[0]?.name === 'Platform';
  const bizId = isPlatform ? 0 : currentBizId;
  const columns = [
    {
      label: t('告警组名称'),
      field: 'name',
      width: 240,
      render: ({ row }: TableRenderData) => {
        const isRenderTag = !isPlatform && row.is_built_in;
        const content = <>
            {
              isRenderTag
                ? <MiniTag
                    content={ t('内置') }
                    class="ml-4" />
                : null
            }
            {
              isNewUser(row.create_at)
                ? <MiniTag
                    content='NEW'
                    theme='success'
                    class="ml-4">
                  </MiniTag>
                : null
            }
        </>;

        return (
          <RenderTextEllipsisOneLine
            text={row.name}
            onText-click={ () => handleOpenDetail('edit', row) }>
            { content }
          </RenderTextEllipsisOneLine>
        );
      },
    },
    {
      label: t('通知对象'),
      field: 'recipient',
      render: ({ row }: TableRenderData) => {
        const userGroup = userGroupMap.value;

        if (Object.keys(userGroup).length) {
          const receivers = row.receivers.map((item) => {
            if (item.type === 'group') {
              return userGroup[item.id];
            }
            return {
              ...item,
              displayName: item.id,
            };
          });

          return <RenderRow data={ receivers } />;
        }
      },
    },
    {
      label: t('应用策略'),
      field: 'relatedPolicyCount',
      width: 100,
      render: ({ row }: TableRenderData) => {
        const { used_count: usedCount } = row;

        return (
          usedCount
            ? <bk-button
              text
              theme="primary"
              onClick={ () => toRelatedPolicy(row.id, row.db_type) }>
              { usedCount }
            </bk-button>
            : <span>0</span>
        );
      },
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 160,
      sort: true,
      render: ({ row }: TableRenderData) => (<span>{ row.update_at || '--' }</span>),
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 100,
      render: ({ row }: TableRenderData) => (<span>{ row.updater || '--' }</span>),
    },
    {
      label: t('操作'),
      width: 180,
      render: ({ row }: TableRenderData) => {
        const tipDisabled = isPlatform || !row.is_built_in;
        const btnDisabled = (!isPlatform && row.is_built_in) || row.used_count > 0;
        const tips = {
          disabled: tipDisabled,
          content: t('内置告警不支持删除'),
        };

        return (
          <>
            <bk-button
              class="mr-24"
              text
              theme="primary"
              onClick={ () => handleOpenDetail('edit', row) }>
              { t('编辑') }
            </bk-button>
            <bk-button
              class="mr-24"
              text
              theme="primary"
              onClick={ () => handleOpenDetail('copy', row) }>
              { t('克隆') }
            </bk-button>
            <span v-bk-tooltips={ tips }>
              <bk-button
                text
                disabled={ btnDisabled }
                theme="primary"
                onClick={ () => handleDelete(row.id) }>
                { t('删除') }
              </bk-button>
            </span>
          </>
        );
      },
    },
  ];

  const tableRef = ref();
  const keyword = ref('');
  const detailDialogShow = ref(false);
  const detailType = ref<'add' | 'edit' | 'copy'>('add');
  const detailData = ref({} as AlarmGroupItem);
  const nameList = ref<string[]>([]);
  const userGroupMap = shallowRef<UserGroupMap>({});

  useRequest(getUserGroupList, {
    defaultParams: [{ bizId }],
    onSuccess(userGroupList) {
      userGroupMap.value = userGroupList.reduce((userGroupPrev, userGroup) => ({ ...userGroupPrev, [userGroup.id]: {
        id: userGroup.id,
        displayName: userGroup.display_name,
        type: userGroup.type,
      },
      }), {} as UserGroupMap);
    },
  });

  const fetchTableData = () => {
    tableRef.value.fetchData({
      name: keyword.value,
    }, {
      bk_biz_id: bizId,
    });
  };

  const setRowClass = (row: AlarmGroupItem) => (isNewUser(row.create_at) ? 'is-new' : '');

  const toRelatedPolicy = (notifyGroupId: number, dbType: string) => {
    const routerData = router.resolve({
      name: 'DBMonitorStrategy',
      params: {
        bizId: currentBizId,
      },
      query: {
        notifyGroupId,
        dbType,
      },
    });

    window.open(routerData.href, '_blank');
  };

  const handleOpenDetail = (type: 'add' | 'edit' | 'copy', row?: AlarmGroupItem) => {
    detailDialogShow.value = true;
    detailType.value = type;
    if (row) {
      detailData.value = row;
    }
  };

  const handleDelete = (id: number) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该告警组'),
      content: t('删除后将无法恢复'),
      onConfirm: async () => {
        try {
          await deleteAlarmGroup({ id });
          messageSuccess(t('删除成功'));
          fetchTableData();
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  const handleRequestSuccess = (tableData: ListBase<AlarmGroupItem[]>) => {
    nameList.value = tableData.results.map(tableItem => tableItem.name);
  };

  onMounted(() => {
    fetchTableData();
  });
</script>

<style lang="less" scoped>
  .alert-group {
    .alert-group-operations {
      display: flex;

      .search-input {
        width: 500px;
        margin-left: auto;
      }
    }

    :deep(.alert-group-table) {
      .name-cell {
        display: flex;
        align-items: center;

        .name-button {
          display: block;
          overflow: hidden;
          line-height: 1.5;
          flex: 0 1 auto;

          .bk-button-text {
            display: block;
            overflow: hidden;
            line-height: inherit;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
      }

      .is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }
    }
  }
</style>
