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
        @click="handleAdd">
        {{ t('新建') }}
      </BkButton>
      <BkInput
        v-model="keyword"
        class="search-input"
        clearable
        :placeholder="t('请输入策略名称')"
        type="search"
        @clear="fetchTableData"
        @enter="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      class="alert-group-table"
      :columns="columns"
      :data-source="getAlarmGroupList" />
    <DetailDialog
      v-model="detailDialogShow"
      :biz-id="bizId"
      :detail-data="detailData"
      :title="detailTitle"
      :type="detailType"
      @successed="fetchTableData" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    deleteAlarmGroup,
    getAlarmGroupList,
    getUserGroupList,
  } from '@services/monitorAlarm';

  import { useInfoWithIcon } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageSuccess } from '@utils';

  import DetailDialog from './components/DetailDialog.vue';
  import RenderRow from './components/RenderRow.vue';

  type AlarmGroupItem = ServiceReturnType<typeof getAlarmGroupList>['results'][number]

  interface TableRenderData {
    row: AlarmGroupItem
  }

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const route = useRoute();
  const router = useRouter();

  const columns = [
    {
      label: t('警告组名称'),
      field: 'name',
      width: 240,
      render: ({ row }: TableRenderData) => {
        const isRenderTag = !isPlatform.value && row.is_built_in;

        return (
          <>
            <span class="alarm-group-name">{ row.name }</span>
            {
              isRenderTag
                ? <bk-tag class="ml-4">{ t('内置')}</bk-tag>
                : null
              }
          </>
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
        const { related_policy_count: relatedPolicyCount } = row;

        return (
            <bk-button
              text
              theme="primary"
              onClick={ () => toRelatedPolicy(row.id) }>
              { relatedPolicyCount || 0 }
            </bk-button>
        );
      },
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 160,
      sort: true,
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 100,
    },
    {
      label: t('操作'),
      width: 150,
      render: ({ row }: TableRenderData) => {
        const tipDisabled = isPlatform.value || !row.is_built_in;
        const btnDisabled = (!isPlatform.value && row.is_built_in) || row.related_policy_count > 0;
        const tips = {
          disabled: tipDisabled,
          content: t('内置告警不支持删除'),
        };

        return (
          <>
            <bk-button
              class="mr-8"
              text
              theme="primary"
              onClick={ () => handleEdit(row) }>
              { t('编辑') }
            </bk-button>
            <bk-button
              class="mr-8"
              text
              theme="primary"
              onClick={ () => handleCopy(row) }>
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
  const detailTitle = ref('');
  const detailType = ref<'add' | 'edit' | 'copy' | ''>('');
  const detailData = ref({} as AlarmGroupItem);

  const isPlatform = computed(() => route.matched[0]?.name === 'Platform');
  const bizId = computed(() => (isPlatform.value ? 0 : currentBizId));
  const userGroupMap = computed(() => (userGroupList.value || []).reduce((userGroupPrev, userGroup) => {
    Object.assign(userGroupPrev, {
      [userGroup.id]: {
        id: userGroup.id,
        displayName: userGroup.display_name,
        type: userGroup.type,
      },
    });

    return userGroupPrev;
  }, {} as {
    [key: string]: {
      id: string,
      displayName: string,
      type: string
    }
  }));

  const { data: userGroupList } = useRequest(getUserGroupList, {
    defaultParams: [bizId.value],
  });

  const fetchTableData = () => {
    tableRef.value.fetchData({
      name: keyword.value,
    }, {
      bk_biz_id: bizId.value,
    });
  };

  const toRelatedPolicy = (notifyGroupId: number) => {
    const routerData = router.resolve({
      name: 'DBMonitorStrategy',
      params: {
        notifyGroupId,
      },
    });

    window.open(routerData.href, '_blank');
  };

  const handleAdd = () => {
    detailDialogShow.value = true;
    detailType.value = 'add';
    detailTitle.value = t('新建警告组');
  };

  const handleEdit = (data: AlarmGroupItem) => {
    detailDialogShow.value = true;
    detailType.value = 'edit';
    detailTitle.value = t('编辑警告组');
    detailData.value = data;
  };

  const handleCopy = (data: AlarmGroupItem) => {
    detailDialogShow.value = true;
    detailType.value = 'copy';
    detailTitle.value = `${t('克隆警告组')}【${data.name}】`;
    detailData.value = data;
  };

  const handleDelete = (id: number) => {
    useInfoWithIcon({
      type: 'warnning',
      title: t('确认删除该告警组'),
      content: t('删除后将无法恢复'),
      onConfirm: async () => {
        try {
          await deleteAlarmGroup(id);
          messageSuccess(t('删除成功'));
          fetchTableData();
          return true;
        } catch (_) {
          return false;
        }
      },
    });
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
      .alarm-group-name {
        color: @primary-color;
      }
    }
  }
</style>
