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
  <div class="whitelist-page">
    <BkAlert
      closable
      theme="warning"
      :title="
        t('如果希望使用通配符授权一批IP_或者授权平台公共类IP_未注册到配置平台的IP_需要先录入到白名单中_才能对其授权')
      " />
    <div class="whitelist-operations">
      <AuthButton
        :action-id="managePermissionActionId"
        theme="primary"
        @click="handleCreate">
        {{ t('新建') }}
      </AuthButton>
      <span
        v-bk-tooltips="{
          disabled: selectedIdList.length > 0,
          content: t('请选择白名单组'),
        }"
        class="delete-button">
        <AuthButton
          :action-id="managePermissionActionId"
          class="ml-8"
          :disabled="selectedIdList.length < 1"
          @click="handleBatchDelete">
          {{ t('批量删除') }}
        </AuthButton>
      </span>
      <BkInput
        v-model="keyword"
        clearable
        :placeholder="t('请输入IP')"
        style="width: 500px"
        type="search"
        @clear="fetchTableData"
        @enter="fetchTableData" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getWhitelist"
      :disable-select-method="disableSelectMethod"
      selectable
      @clear-search="handleClearSearch"
      @selection="handleTableSelection" />
  </div>
  <WhitelistOperation
    v-model:is-show="operationState.isShow"
    :biz-id="bizId"
    :data="operationState.data"
    :is-edit="operationState.isEdit"
    :title="operationState.title"
    @successed="fetchTableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import IpWhiteModel from '@services/model/ip-white/ip-white';
  import {
    batchDeleteWhitelist,
    getWhitelist,
  } from '@services/source/whitelist';

  import { useCopy, useInfoWithIcon } from '@hooks';

  import RenderRow from '@components/render-row/index.vue';

  import {
    messageSuccess,
  } from '@utils';

  import WhitelistOperation from './components/WhitelistOperation.vue';

  interface TableRenderData {
    data: IpWhiteModel
  }

  const route = useRoute();
  const copy = useCopy();
  const { t } = useI18n();

  const isPlatformManage = route.name === 'PlatformWhitelist';
  const bizId = isPlatformManage ? 0 : window.PROJECT_CONFIG.BIZ_ID;
  const managePermissionActionId = isPlatformManage ? 'global_ip_whitelist_manage' : 'ip_whitelist_manage';

  const tableRef = ref();
  const keyword = ref('');
  const selectedIdList = shallowRef<number[]>([]);

  const operationState = reactive({
    isShow: false,
    title: t('新建白名单'),
    isEdit: false,
    data: {} as IpWhiteModel,
  });

  const disableSelectMethod = (row: IpWhiteModel) => ((row.is_global && !isPlatformManage)
    ? t('全局白名单如需编辑请联系平台管理员')
    : false);

  const columns = [
    {
      label: t('IP或IP%'),
      field: 'ips',
      showOverflowTooltip: false,
      render: ({ data }: TableRenderData) => {
        const isRenderTag = data.is_global && !isPlatformManage;
        return (
          <>
            <RenderRow style={`max-width: calc(100% - ${isRenderTag ? '80px' : '20px'});`} data={data.ips} />
            { isRenderTag && (
              <bk-tag class="ml-4">
                {t('全局')}
              </bk-tag>
            )}
            <db-icon
              v-bk-tooltips={t('复制')}
              type="copy"
              class="copy-btn"
              onClick={() => copy(data.ips.join('\n'))} />
          </>
        );
      },
    },
    {
      label: t('备注'),
      field: 'remark',
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 180,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 180,
      render: ({ data }: TableRenderData) => data.updateAtDisplay || '--',
    },
    {
      label: t('操作'),
      field: 'operations',
      width: 140,
      render: ({ data }: TableRenderData) => {
        const isDisabled = data.is_global && !isPlatformManage;
        const tips = {
          disabled: !isDisabled,
          content: t('全局白名单如需编辑请联系平台管理员'),
        };

        return (
          <>
            <span v-bk-tooltips={tips}>
              <auth-button
                action-id={managePermissionActionId}
                permission={data.permission[managePermissionActionId]}
                class="mr-8"
                text
                theme="primary"
                disabled={isDisabled}
                onClick={() => handleEdit(data)}>
                {t('编辑')}
              </auth-button>
            </span>
            <span v-bk-tooltips={tips}>
              <auth-button
                action-id={managePermissionActionId}
                permission={data.permission[managePermissionActionId]}
                text
                theme="primary"
                disabled={isDisabled}
                onClick={() => handleDelete([data.id])}>
                {t('删除')}
              </auth-button>
            </span>
          </>
        );
      },
    },
  ];

  const fetchTableData = () => {
    tableRef.value.fetchData({
      ip: keyword.value,
    }, {
      bk_biz_id: bizId,
    });
  };

  const handleCreate = () => {
    operationState.isShow = true;
    operationState.title = t('新建白名单');
    operationState.isEdit = false;
  };

  const handleBatchDelete = () => {
    handleDelete(selectedIdList.value);
  };

  const handleTableSelection = (idList: number[]) => {
    selectedIdList.value = idList;
  };

  const handleEdit = (data: IpWhiteModel) => {
    operationState.isShow = true;
    operationState.title = t('编辑白名单');
    operationState.isEdit = true;
    operationState.data = data;
  };

  const handleDelete = (ids: number[]) => {
    const isSingle = ids.length === 1;
    useInfoWithIcon({
      type: 'warnning',
      title: isSingle ? t('确认删除该组白名单') : t('确认删除该组白名单', [ids.length]),
      content: t('白名单删除后_不会影响现已授权实例_新增授权时将无法再选择_请谨慎操作'),
      onConfirm: async () => {
        try {
          await batchDeleteWhitelist({ ids });
          messageSuccess(t('删除成功'));
          fetchTableData();
          return true;
        } catch (_) {
          return false;
        }
      },
    });
  };

  const handleClearSearch = () => {
    keyword.value = '';
    fetchTableData();
  };

  onMounted(() => {
    fetchTableData();
  });
</script>

<style lang="less">
  .whitelist-page {
    .bk-table {
      tr:hover {
        .copy-btn {
          display: inline-block;
        }
      }

      .copy-btn {
        display: none;
        color: @primary-color;
        cursor: pointer;
      }
    }

    .whitelist-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 0;

      .delete-button {
        margin-right: auto;
      }

      .bk-button {
        min-width: 88px;
        margin-right: 8px;
      }
    }
  }
</style>
