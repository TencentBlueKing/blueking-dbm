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

  import { useInfoWithIcon } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { messageSuccess } from '@utils';

  import {
    deleteAlarmGroup,
    getAlarmGroupList,
    getRelatedPolicy,
    getUserGroupList,
  } from './common/services';
  import type { AlarmGroupItem } from './common/types';
  import DetailDialog from './components/DetailDialog.vue';
  import RenderRow from './components/RenderRow.vue';

  interface TableRenderData {
    data: AlarmGroupItem
  }

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const route = useRoute();
  const router = useRouter();

  const isPlatform = computed(() => route.matched[0]?.name === 'Platform');
  const bizId = computed(() => (isPlatform.value ? 0 : currentBizId));

  const tableRef = ref();
  const detailDialogShow = ref(false);
  const detailTitle = ref('');
  const detailType = ref<'add' | 'edit' | 'copy' | ''>('');
  const keyword = ref('');

  const { data: userGroupList } = useRequest(getUserGroupList, {
    defaultParams: [bizId.value],
  });
  const userGroupMap = computed(() => {
    const initData: {
      [key: string]: {
        id: string,
        displayName: string,
        type: string
      }
    } = {};

    return userGroupList.value?.reduce((prev, current) => {
      Object.assign(prev, {
        [current.id]: {
          id: current.id,
          displayName: current.display_name,
          type: current.type,
        },
      });

      return prev;
    }, initData) || initData;
  });

  onMounted(() => {
    fetchTableData();
  });

  const fetchTableData = () => {
    tableRef.value.fetchData({
      name: keyword.value,
    }, {
      bk_biz_id: bizId.value,
    });
  };

  const columns = [
    {
      label: t('警告组名称'),
      field: 'name',
      width: 240,
      render: ({ data }: TableRenderData) => {
        const isRenderTag = !isPlatform.value && data.is_built_in;

        return (
          <>
            <span class="name">{ data.name }</span>
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
      render: ({ data }: TableRenderData) => {
        const userGroup = userGroupMap.value;

        if (Object.keys(userGroup).length) {
          const receivers = data.receivers.map((item) => {
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
      render: ({ data }: TableRenderData) => {
        const { related_policy_count: relatedPolicyCount } = data;

        return (
          <bk-popover
            disabled= { !relatedPolicyCount }
            placement="top"
            theme="light"
            allowHTML
            onAfterShow={ handlePolicyShow }
            content={ (relatedPolicyList.value || []).map(item => (
              <p
                key={ item.id }
                class="mt-4 mb-4">
                { item.name }
              </p>
            ))}>
            <bk-button
              text
              theme="primary"
              onClick={ toRelatedPolicy }>
              { relatedPolicyCount || 0 }
            </bk-button>
          </bk-popover>
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
      render: ({ data }: TableRenderData) => {
        const tipDisabled = isPlatform.value || !data.is_built_in;
        const btnDisabled = (!isPlatform.value && data.is_built_in) || data.related_policy_count > 0;
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
              onClick={ () => handleEdit(data) }>
              { t('编辑') }
            </bk-button>
            <bk-button
              class="mr-8"
              text
              theme="primary"
              onClick={ () => handleCopy(data) }>
              { t('克隆') }
            </bk-button>
            <span v-bk-tooltips={ tips }>
              <bk-button
                text
                disabled={ btnDisabled }
                theme="primary"
                onClick={ () => handleDelete(data.id) }>
                { t('删除') }
              </bk-button>
            </span>
          </>
        );
      },
    },
  ];

  const {
    data: relatedPolicyList,
    run: getRelatedPolicyRun,
  } = useRequest(getRelatedPolicy, {
    manual: true,
  });

  const handlePolicyShow = () => {
    getRelatedPolicyRun();
  };

  const toRelatedPolicy = () => {
    // TODO
    // const routerData = router.resolve({
    //   name: 'resourcePoolList',
    //   query: {
    //     listId: 1,
    //   },
    // });

    // window.open(routerData.href, '_blank');
  };

  const detailData = ref({} as AlarmGroupItem);

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
      .name {
        color: @primary-color;
      }
    }
  }
</style>
