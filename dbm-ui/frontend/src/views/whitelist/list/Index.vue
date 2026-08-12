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
        @clear="handleKeyWordChange"
        @enter="handleKeyWordChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getWhitelist"
      :disable-select-method="disableSelectMethod"
      row-key="id"
      selectable
      @clear-search="handleClearSearch"
      @selection="handleTableSelection">
      <TableColumn
        col-key="ips"
        :min-width="200"
        :show-overflow="false"
        :title="t('IP或IP%')">
        <template #default="{ row: data }: { row: IpWhiteModel }">
          <RenderRow
            :data="data.ips"
            :style="{ maxWidth: `calc(100% - ${data.is_global && !isPlatformManage ? '80px' : '20px'})` }" />
          <BkTag
            v-if="data.is_global && !isPlatformManage"
            class="ml-4">
            {{ t('全局') }}
          </BkTag>
          <DbIcon
            v-bk-tooltips="t('复制')"
            class="copy-btn"
            type="copy"
            @click="execCopy(data.ips.join('\n'), t('复制成功，共n条', { n: data.ips.length }))" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="remark"
        :min-width="150"
        :title="t('备注')">
      </TableColumn>
      <TableColumn
        col-key="updater"
        :title="t('更新人')"
        :width="120">
      </TableColumn>
      <TableColumn
        col-key="update_at"
        :title="t('更新时间')"
        :width="180">
        <template #default="{ row: data }: { row: IpWhiteModel }">
          {{ data.updateAtDisplay || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operations"
        :title="t('操作')"
        :width="140">
        <template #default="{ row: data }: { row: IpWhiteModel }">
          <span
            v-bk-tooltips="{
              content: t('全局白名单如需编辑请联系平台管理员'),
              disabled: !(data.is_global && !isPlatformManage),
            }">
            <AuthButton
              :action-id="managePermissionActionId"
              class="mr-8"
              :disabled="data.is_global && !isPlatformManage"
              :permission="data.permission[managePermissionActionId]"
              text
              theme="primary"
              @click="handleEdit(data)">
              {{ t('编辑') }}
            </AuthButton>
          </span>
          <span
            v-bk-tooltips="{
              content: t('全局白名单如需编辑请联系平台管理员'),
              disabled: !(data.is_global && !isPlatformManage),
            }">
            <AuthButton
              :action-id="managePermissionActionId"
              :disabled="data.is_global && !isPlatformManage"
              :permission="data.permission[managePermissionActionId]"
              text
              theme="primary"
              @click="handleDelete([data.id])">
              {{ t('删除') }}
            </AuthButton>
          </span>
        </template>
      </TableColumn>
    </DbTable>
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
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import IpWhiteModel from '@services/model/ip-white/ip-white';
  import { batchDeleteWhitelist, getWhitelist } from '@services/source/whitelist';

  import DbTable from '@components/db-table/IndexNew.vue';
  import RenderRow from '@components/render-row/index.vue';

  import { execCopy, messageSuccess } from '@utils';

  import WhitelistOperation from './components/WhitelistOperation.vue';

  const route = useRoute();
  const { t } = useI18n();

  const isPlatformManage = route.name === 'PlatformWhitelist';
  const bizId = isPlatformManage ? 0 : window.PROJECT_CONFIG.BIZ_ID;
  const managePermissionActionId = isPlatformManage ? 'global_ip_whitelist_manage' : 'ip_whitelist_manage';

  const tableRef = ref();
  const keyword = ref('');
  const selectedIdList = shallowRef<number[]>([]);

  const operationState = reactive({
    data: {} as IpWhiteModel,
    isEdit: false,
    isShow: false,
    title: t('新建白名单'),
  });

  const disableSelectMethod = (row: IpWhiteModel) =>
    row.is_global && !isPlatformManage ? t('全局白名单如需编辑请联系平台管理员') : false;

  const handleKeyWordChange = () => {
    // tableRef.value!.clearSelected();
    fetchTableData();
  };

  const fetchTableData = () => {
    tableRef.value.fetchData({
      bk_biz_id: bizId,
      ip: keyword.value,
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

  const handleTableSelection = (idList: string[], list: IpWhiteModel[]) => {
    selectedIdList.value = list.map((item) => item.id);
  };

  const handleEdit = (data: IpWhiteModel) => {
    operationState.isShow = true;
    operationState.title = t('编辑白名单');
    operationState.isEdit = true;
    operationState.data = data;
  };

  const handleDelete = (ids: number[]) => {
    const isSingle = ids.length === 1;
    InfoBox({
      content: t('白名单删除后_不会影响现已授权实例_新增授权时将无法再选择_请谨慎操作'),
      onConfirm: async () => {
        try {
          await batchDeleteWhitelist({ ids });
          messageSuccess(t('删除成功'));
          fetchTableData();
          return true;
        } catch {
          return false;
        }
      },
      title: isSingle ? t('确认删除该组白名单') : t('确认删除该组白名单', [ids.length]),
      type: 'warning',
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
    .bk-vxe-table {
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
