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
  <div class="resource-spce-list">
    <div class="resource-spce-operations">
      <AuthButton
        action-id="spec_create"
        class="w-88 mr-8"
        :resource="dbType"
        theme="primary"
        @click="() => handleShowSpecOperation('create')">
        {{ t('新建') }}
      </AuthButton>
      <span
        v-bk-tooltips="{
          content: t('请选择xx', [t('规格')]),
          disabled: hasSelected,
        }">
        <BkButton
          class="w-88 mr-8"
          :disabled="!hasSelected"
          @click="handleBacthDelete">
          {{ t('删除') }}
        </BkButton>
      </span>
      <span
        v-bk-tooltips="{
          content: t('请选择xx', [t('规格')]),
          disabled: hasSelected,
        }"
        class="delete-button">
        <BkButton
          class="w-88 mr-8"
          :disabled="!hasSelected"
          @click="handleBacthEnable">
          {{ t('启用') }}
        </BkButton>
      </span>
      <div class="enable-checkbox">
        <BkCheckbox
          v-model="isEnableSpec"
          class="mr-6"
          @change="fetchData" />
        {{ t('仅显示已启用的规格') }}
      </div>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="t('请输入xx', [t('规格名称')])"
        style="width: 500px"
        type="search"
        @enter="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getResourceSpecList"
      :disable-select-method="disableSelectMethod"
      primary-key="spec_id"
      :row-class="setRowClass"
      selectable
      :settings="settings"
      show-settings
      @clear-search="handleClearSearch"
      @selection="handleSelectionChange"
      @setting-change="updateTableSettings">
      <BkTableColumn
        field="spec_id"
        fixed="left"
        label="ID">
      </BkTableColumn>
      <BkTableColumn
        field="spec_name"
        fixed="left"
        :label="t('规格名称')"
        :width="180">
        <template #default="{ data }: { data: ResourceSpecModel }">
          <TextOverflowLayout>
            <AuthButton
              action-id="spec_update"
              :permission="data.permission.spec_update"
              :resource="dbType"
              text
              theme="primary"
              @click="() => handleShowSpecOperation('edit', data)">
              {{ data.spec_name }}
            </AuthButton>
            <template #append>
              <span
                v-if="data.isRecentSeconds"
                class="glob-new-tag ml-4"
                data-text="NEW" />
            </template>
          </TextOverflowLayout>
        </template>
      </BkTableColumn>
      <ModelColumn :label="machineTypeLabel" />
      <BkTableColumn
        field="desc"
        :label="t('描述')"
        :width="100">
        <template #default="{ data }: { data: ResourceSpecModel }">
          {{ data.desc || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        v-if="hasInstance"
        field="instance_num"
        :label="t('每台主机实例数量')"
        :width="140">
      </BkTableColumn>
      <BkTableColumn
        v-if="hasQPS"
        field="qpsText"
        :label="t('单机QPS')"
        :width="140">
      </BkTableColumn>
      <BkTableColumn
        field="enable"
        :label="t('是否启用')"
        :width="120">
        <template #default="{ data }: { data: ResourceSpecModel }">
          <BkPopConfirm
            :confirm-text="data.enable ? t('停用') : t('启用')"
            :content="
              data.enable
                ? t('停用后，在资源规格选择时，将不可见，且不可使用')
                : t('启用后，在资源规格选择时，将开放选择')
            "
            placement="bottom"
            :title="data.enable ? t('确认停用该规格？') : t('确认启用该规格？')"
            trigger="click"
            width="308"
            @confirm="() => handleConfirmSwitch(data)">
            <AuthSwitcher
              action-id="spec_update"
              :model-value="data.enable"
              :permission="data.permission.spec_update"
              :resource="dbType"
              size="small"
              theme="primary" />
          </BkPopConfirm>
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="update_at"
        :label="t('更新时间')"
        sort
        :width="250">
        <template #default="{ data }: { data: ResourceSpecModel }">
          {{ data.updateAtDisplay }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="updater"
        :label="t('更新人')"
        sort
        :width="250">
        <template #default="{ data }: { data: ResourceSpecModel }">
          {{ data.updater || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field=""
        fixed="right"
        :label="t('操作')"
        :width="120">
        <template #default="{ data }: { data: ResourceSpecModel }">
          <AuthButton
            action-id="spec_update"
            class="mr-12"
            :permission="data.permission.spec_update"
            :resource="dbType"
            text
            theme="primary"
            @click="() => handleShowSpecOperation('edit', data)">
            {{ t('编辑') }}
          </AuthButton>
          <AuthButton
            action-id="spec_create"
            class="mr-12"
            :permission="data.permission.spec_create"
            :resource="dbType"
            text
            theme="primary"
            @click="() => handleShowSpecOperation('clone', data)">
            {{ t('克隆') }}
          </AuthButton>
          <span
            v-if="data.is_refer"
            v-bk-tooltips="t('该规格已被使用_无法删除')"
            class="inline-block;">
            <AuthButton
              action-id="spec_delete"
              disabled
              :permission="data.permission.spec_delete"
              :resource="dbType"
              text
              theme="primary">
              {{ t('删除') }}
            </AuthButton>
          </span>
          <AuthButton
            v-else
            action-id="spec_delete"
            :permission="data.permission.spec_delete"
            :resource="dbType"
            text
            theme="primary"
            @click="() => handleDelete([data], false)">
            {{ t('删除') }}
          </AuthButton>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
  <BkSideslider
    v-model:is-show="isSpecOperationShow"
    :before-close="handleBeforeClose"
    render-directive="if"
    :width="960">
    <template #header>
      <template v-if="specOperationMode === 'edit'">
        <span>{{ t('编辑规格') }} 【{{ specOperationData?.spec_name }}】</span>
      </template>
      <template v-else-if="specOperationMode === 'clone'">
        <span>{{ t('克隆规格') }} 【{{ specOperationData?.spec_name }}】</span>
      </template>
      <template v-else>
        {{ t('新增规格') }}
      </template>
      <BkTag
        class="ml-4"
        theme="info">
        {{ dbTypeLabel }}
      </BkTag>
    </template>
    <SpecOperaion
      :key="specOperationData?.spec_id"
      :data="specOperationData"
      :db-type="dbType"
      :has-instance="hasInstance"
      :machine-type="machineType"
      :machine-type-label="machineTypeLabel"
      :mode="specOperationMode"
      @cancel="handleCloseSpecOperation"
      @successed="handleSubmitSuccessed" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import {
    batchDeleteResourceSpec,
    getResourceSpecList,
    updateResourceSpecEnableStatus,
  } from '@services/source/dbresourceSpec';

  import { useBeforeClose, useDebouncedRef, useTableSettings } from '@hooks';

  import { DBTypes, UserPersonalSettings } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import ModelColumn from './components/ModelColumn.vue';
  import SpecOperaion from './components/spec-operation/Index.vue';
  import { useHasQPS } from './hooks/useHasQPS';

  type SpecOperationType = 'create' | 'edit' | 'clone';

  interface Props {
    dbType: DBTypes;
    dbTypeLabel: string;
    machineType: string;
    machineTypeLabel: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { hasQPS } = useHasQPS(props);
  const handleBeforeClose = useBeforeClose();
  const searchKey = useDebouncedRef('');

  const disableSelectMethod = (row: ResourceSpecModel) => (row.is_refer ? t('该规格已被使用_无法删除') : false);
  const setRowClass = (data: ResourceSpecModel) => (data.isRecentSeconds ? 'is-new-row' : '');

  const tableRef = ref();
  const isEnableSpec = ref(true);
  const isSpecOperationShow = ref(false);
  const specOperationMode = ref<SpecOperationType>('create');

  const specOperationData = shallowRef<ResourceSpecModel>();
  const selectedList = shallowRef<ResourceSpecModel[]>([]);

  const hasSelected = computed(() => selectedList.value.length > 0);
  const hasInstance = computed(() => [`${DBTypes.ES}_es_datanode`].includes(`${props.dbType}_${props.machineType}`));

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.SPECIFICATION_TABLE_SETTINGS, {
    checked: ['spec_id', 'spec_name', 'model', 'desc', 'instance_num', 'qpsText', 'enable', 'update_at', 'updater'],
    disabled: ['model', 'spec_name'],
  });

  const { run: runUpdateResourceSpec } = useRequest(updateResourceSpecEnableStatus, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchData();
    },
  });

  watch(
    () => [props.dbType, props.machineType, searchKey],
    () => {
      tableRef.value!.clearSelected();
      fetchData();
    },
  );

  const handleConfirmSwitch = (row: ResourceSpecModel) => {
    runUpdateResourceSpec({
      enable: !row.enable,
      spec_ids: [row.spec_id],
    });
  };

  const fetchData = () => {
    const params = {
      spec_cluster_type: props.dbType,
      spec_machine_type: props.machineType,
    };
    if (isEnableSpec.value) {
      Object.assign(params, { enable: isEnableSpec.value });
    }
    tableRef.value.fetchData(
      {
        spec_name: searchKey.value,
      },
      params,
    );
  };

  const handleSelectionChange = (idList: number[], list: ResourceSpecModel[]) => {
    selectedList.value = list;
  };

  const handleShowSpecOperation = (mode: UnwrapRef<typeof specOperationMode>, data?: ResourceSpecModel) => {
    isSpecOperationShow.value = true;
    specOperationMode.value = mode;
    specOperationData.value = data;
  };

  const handleSubmitSuccessed = () => {
    isSpecOperationShow.value = false;
    fetchData();
  };

  const handleCloseSpecOperation = async () => {
    const allowClose = await handleBeforeClose();
    if (allowClose) {
      isSpecOperationShow.value = false;
    }
  };

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const handleBacthDelete = () => {
    handleDelete(selectedList.value);
  };

  const handleBacthEnable = () => {
    runUpdateResourceSpec({
      enable: true,
      spec_ids: selectedList.value.map((item) => item.spec_id),
    });
  };

  const handleDelete = (list: ResourceSpecModel[], isBatch = true) => {
    InfoBox({
      content: () => (
        <>
          {list.map((item) => (
            <p>{item.spec_name}</p>
          ))}
        </>
      ),
      onConfirm: async () => {
        try {
          await batchDeleteResourceSpec({
            spec_ids: isBatch ? selectedList.value.map((item) => item.spec_id) : list.map((item) => item.spec_id),
          });
          messageSuccess(t('删除成功'));
          fetchData();
          return true;
        } catch {
          return false;
        }
      },
      title: t('确认删除以下规格'),
      type: 'warning',
    });
  };
</script>

<style lang="less" scoped>
  .resource-spce-list {
    padding: 16px 24px 0;
    background-color: white;

    .resource-spce-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 16px;

      .delete-button {
        margin-right: auto;
      }

      .enable-checkbox {
        display: flex;
        margin-right: 16px;
        font-size: 12px;
        color: #4d4f56;
        align-items: center;
      }
    }

    :deep(.machine-info) {
      .bk-tag {
        &:hover {
          background-color: #f0f1f5;
        }

        &.bk-tag-info {
          background-color: #edf4ff;
        }
      }

      &:hover {
        background-color: #f0f1f5;
      }
    }
  }
</style>
