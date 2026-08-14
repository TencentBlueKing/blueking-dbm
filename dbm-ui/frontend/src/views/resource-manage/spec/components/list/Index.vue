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
    <div class="resource-spec-operations">
      <AuthButton
        action-id="spec_create"
        class="w-88"
        :resource="dbType"
        theme="primary"
        @click="() => handleShowSpecOperation('create')">
        {{ t('新建') }}
      </AuthButton>
      <BkDropdown
        v-bk-tooltips="{
          disabled: !disabled,
          content: t('请选择规格'),
        }"
        class="batch-operation ml-8"
        :disabled="disabled"
        :popover-options="{
          clickContentAutoHide: true,
          renderDirective: 'show',
        }"
        trigger="click">
        <template #default="{ popoverShow }">
          <BkButton :disabled="disabled">
            {{ t('批量操作') }}
            <DbIcon
              class="batch-operation-icon ml-4"
              :class="[{ 'batch-operation-icon-active': popoverShow }]"
              type="up-big " />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BatchSwithEnable
                :data-list="selectedList"
                :db-type="dbType"
                enable
                @success="fetchData" />
            </BkDropdownItem>
            <BkDropdownItem>
              <BatchSwithEnable
                :data-list="selectedList"
                :db-type="dbType"
                :enable="false"
                @success="fetchData" />
            </BkDropdownItem>
            <BkDropdownItem
              v-bk-tooltips="{
                content: batchDeleteTooltips,
                disabled: !batchDeleteTooltips,
                placement: 'right',
              }">
              <BkButton
                class="opration-button"
                :disabled="!!batchDeleteTooltips"
                text
                @click="handleBacthDelete">
                {{ t('删除规格') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem v-if="isShowReplenish">
              <BatchSwithReplenish
                :data-list="selectedList"
                :db-type="dbType"
                need-replenish
                @success="fetchData" />
            </BkDropdownItem>
            <BkDropdownItem v-if="isShowReplenish">
              <BatchSwithReplenish
                :data-list="selectedList"
                :db-type="dbType"
                :need-replenish="false"
                @success="fetchData" />
            </BkDropdownItem>
            <BkDropdownItem v-if="isShowReplenish">
              <BatchSetRatio
                :data-list="selectedList"
                :db-type="dbType"
                :ratio-map="ratioMap"
                @success="fetchData" />
            </BkDropdownItem>
            <BkDropdownItem>
              <BatchEditBizScope
                :data-list="selectedList"
                :db-type="dbType"
                @success="fetchData" />
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <div class="enable-checkbox">
        <BkCheckbox
          v-model="isEnableSpec"
          class="mr-6"
          @change="fetchData" />
        {{ t('仅显示已启用的规格') }}
      </div>
      <DbSearchSelect
        class="ml-8"
        :data="searchData"
        :model-value="searchValue"
        :placeholder="t('搜索ID，规格名称，应用范围，业务')"
        style="width: 500px"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :bk-ui-settings="settings"
      :data-source="getResourceSpecList"
      releate-url-query
      :row-class-name="setRowClass"
      row-key="spec_id"
      :scroll="{ type: 'virtual' }"
      selectable
      :show-overflow="false"
      @bk-ui-settings-change="updateTableSettings"
      @clear-search="handleClearSearch"
      @selection="handleSelectionChange">
      <TableColumn
        col-key="spec_id"
        fixed="left"
        title="ID">
      </TableColumn>
      <TableColumn
        col-key="spec_name"
        fixed="left"
        :title="t('规格名称')"
        :width="180">
        <template #default="{ row }: { row: ResourceSpecModel }">
          <TextOverflowLayout>
            <AuthButton
              action-id="spec_manage"
              :permission="row.permission.spec_manage"
              :resource="dbType"
              text
              theme="primary"
              @click="() => handleShowSpecOperation('edit', row)">
              {{ row.spec_name }}
            </AuthButton>
            <template #append>
              <BkTag
                v-if="row.isRecentSeconds"
                class="ml-4"
                size="small"
                theme="success">
                NEW
              </BkTag>
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <ModelColumn :title="machineTypeLabel" />
      <BizScopeColumn />
      <TableColumn
        v-if="hasInstance"
        col-key="instance_num"
        :title="t('每台主机实例数量')"
        :width="140">
      </TableColumn>
      <TableColumn
        v-if="hasQPS"
        col-key="qpsText"
        :title="t('单机QPS')"
        :width="140">
      </TableColumn>
      <TableColumn
        col-key="enable"
        :title="t('启停')"
        :width="120">
        <template #default="{ row }: { row: ResourceSpecModel }">
          <BkPopConfirm
            :confirm-text="row.enable ? t('停用') : t('启用')"
            :content="
              row.enable
                ? t('停用后，存量集群的变更操作不受影响，新增集群不可使用此规格')
                : t('启用后，所有场景均可使用，如：部署、扩容、迁移规格')
            "
            placement="bottom"
            :title="row.enable ? t('确认停用该规格？') : t('确认启用该规格？')"
            trigger="click"
            width="308"
            @confirm="() => handleConfirmSwitch(row)">
            <AuthSwitcher
              action-id="spec_manage"
              :model-value="row.enable"
              :permission="row.permission.spec_manage"
              :resource="dbType"
              size="small"
              theme="primary" />
          </BkPopConfirm>
        </template>
      </TableColumn>
      <TableColumn
        v-if="isShowReplenish"
        col-key="replensish"
        :title="t('自动补货')"
        :width="120">
        <template #default="{ row }: { row: ResourceSpecModel }">
          <BkPopConfirm
            :confirm-text="row.needReplenish ? t('停用') : t('开启')"
            :content="
              row.needReplenish
                ? t('停用后，当资源池主机数低于资源水位时，不触发自动补货')
                : t('开启后，当资源池主机数低于参考水位时，将自动补货至目标配置')
            "
            placement="bottom"
            :title="row.needReplenish ? t('确认停用自动补货？') : t('确认开启自动补货？')"
            trigger="click"
            width="308"
            @confirm="() => handleConfirmNeedReplenish(row)">
            <BkSwitcher
              v-model="row.needReplenish"
              size="small"
              theme="primary" />
          </BkPopConfirm>
        </template>
      </TableColumn>
      <TableColumn
        v-if="isShowReplenish"
        col-key="ratio"
        :title="t('参考水位')"
        :width="120">
        <template #default="{ row }: { row: ResourceSpecModel }">
          {{ ratioMap ? `${(ratioMap[row.spec_id] ? ratioMap[row.spec_id] : ratioMap['default']) * 100}%` : '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="desc"
        :title="t('描述')"
        :width="100">
        <template #default="{ row }: { row: ResourceSpecModel }">
          {{ row.desc || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="update_at"
        sorter
        :title="t('更新时间')"
        :width="250">
        <template #default="{ row }: { row: ResourceSpecModel }">
          {{ row.updateAtDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updater"
        sorter
        :title="t('更新人')"
        :width="250">
        <template #default="{ row }: { row: ResourceSpecModel }">
          {{ row.updater || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="120">
        <template #default="{ row }: { row: ResourceSpecModel }">
          <AuthButton
            action-id="spec_manage"
            class="mr-12"
            :permission="row.permission.spec_manage"
            :resource="dbType"
            text
            theme="primary"
            @click="() => handleShowSpecOperation('edit', row)">
            {{ t('编辑') }}
          </AuthButton>
          <AuthButton
            action-id="spec_create"
            class="mr-12"
            :permission="row.permission.spec_create"
            :resource="dbType"
            text
            theme="primary"
            @click="() => handleShowSpecOperation('clone', row)">
            {{ t('克隆') }}
          </AuthButton>
          <span
            v-if="row.is_refer"
            v-bk-tooltips="t('仅可删除“未使用”的规格')"
            class="inline-block;">
            <AuthButton
              action-id="spec_manage"
              disabled
              :permission="row.permission.spec_manage"
              :resource="dbType"
              text
              theme="primary">
              {{ t('删除') }}
            </AuthButton>
          </span>
          <AuthButton
            v-else
            action-id="spec_manage"
            :permission="row.permission.spec_manage"
            :resource="dbType"
            text
            theme="primary"
            @click="() => handleDelete([row], false)">
            {{ t('删除') }}
          </AuthButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
  <DbSideslider
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
      :ratio-map="ratioMap"
      @cancel="handleCloseSpecOperation"
      @successed="handleSubmitSuccessed" />
  </DbSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type ResourceSpecModel from '@services/model/resource-spec/resourceSpec';
  import {
    addSpecReplenishTag,
    batchCommonUpdate,
    batchDeleteResourceSpec,
    getResourceSpecList,
    getSpecReplenishRatio,
  } from '@services/source/dbresourceSpec';

  import { useBeforeClose, useLinkQueryColumnSerach, useTableSettings } from '@hooks';

  import { useFunController, useGlobalBizs } from '@stores';

  import { DBTypes, MachineTypes, UserPersonalSettings } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams, messageSuccess } from '@utils';

  import BatchEditBizScope from './components/BatchEditBizScope.vue';
  import BatchSetRatio from './components/BatchSetRatio.vue';
  import BatchSwithEnable from './components/BatchSwithEnable.vue';
  import BatchSwithReplenish from './components/BatchSwithReplenish.vue';
  import BizScopeColumn from './components/BizScopeColumn.vue';
  import ModelColumn from './components/ModelColumn.vue';
  import SpecOperaion from './components/spec-operation/Index.vue';
  import { BizScopesInfoList } from './consts/bizScope';
  import { useHasQPS } from './hooks/useHasQPS';

  type SpecOperationType = 'create' | 'edit' | 'clone';

  interface Props {
    dbType: DBTypes;
    dbTypeLabel: string;
    machineType: MachineTypes;
    machineTypeLabel: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const { hasQPS } = useHasQPS(props);
  const handleBeforeClose = useBeforeClose();
  const funControllerStore = useFunController();

  const { clearSearchValue, handleSearchValueChange, searchValue } = useLinkQueryColumnSerach({
    attrs: [],
    fetchDataFn: () => fetchData(),
    isCluster: false,
    isQueryAttrs: false,
    searchType: 'resource_record',
  });

  const setRowClass = (data: ResourceSpecModel) => (data.isRecentSeconds ? 'is-new-row' : '');

  const isShowReplenish = funControllerStore.funControllerData?.getFlatData('resourceManage').specListReplenish;

  const tableRef = ref();
  const isEnableSpec = ref(true);
  const isSpecOperationShow = ref(false);
  const specOperationMode = ref<SpecOperationType>('create');

  const specOperationData = shallowRef<ResourceSpecModel>();
  const selectedList = shallowRef<ResourceSpecModel[]>([]);

  const disabled = computed(() => selectedList.value.length === 0);

  const hasInstance = computed(() =>
    [`${DBTypes.ES}_${MachineTypes.ES_DATANODE}`].includes(`${props.dbType}_${props.machineType}`),
  );

  const batchDeleteTooltips = computed(() => {
    if (selectedList.value.length === 0) {
      return t('请选择xx', [t('规格')]);
    }
    if (selectedList.value.some((selectItem) => selectItem.is_refer)) {
      return t('仅可删除“未使用”的规格');
    }
    return '';
  });

  const searchData = computed(() => [
    {
      id: 'spec_ids',
      multiple: true,
      name: 'ID',
    },
    {
      id: 'spec_name',
      multiple: true,
      name: t('规格名称'),
    },
    {
      children: BizScopesInfoList.map((bizScopeItem) => ({
        id: bizScopeItem.id,
        name: bizScopeItem.label,
      })),
      id: 'biz_scope',
      name: t('应用范围'),
    },
    {
      children: globalBizsStore.bizs.map((item) => ({
        id: `${item.bk_biz_id}`,
        name: item.name,
      })),
      id: 'biz_ids',
      multiple: true,
      name: t('业务'),
    },
  ]);

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.SPECIFICATION_TABLE_SETTINGS, {
    checked: [
      'spec_id',
      'spec_name',
      'model',
      'desc',
      'instance_num',
      'qpsText',
      'enable',
      'update_at',
      'updater',
      'biz_scope',
      'row-operation',
      'replensish',
      'ratio',
    ],
    disabled: ['model', 'spec_name'],
  });

  const { run: runBatchCommonUpdate } = useRequest(batchCommonUpdate, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchData();
    },
  });

  const { run: runAddSpecReplenishTag } = useRequest(addSpecReplenishTag, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      fetchData();
    },
  });

  const { data: ratioMap, run: fetchRadioMap } = useRequest(getSpecReplenishRatio);

  watch(
    () => [props.dbType, props.machineType],
    () => {
      fetchData();
    },
  );

  const handleConfirmSwitch = (row: ResourceSpecModel) => {
    runBatchCommonUpdate({
      enable: !row.enable,
      spec_ids: [row.spec_id],
    });
  };

  const handleConfirmNeedReplenish = (row: ResourceSpecModel) => {
    runAddSpecReplenishTag({
      need_replenish: !row.needReplenish,
      spec_ids: [row.spec_id],
    });
  };

  const fetchData = () => {
    // tableRef.value!.clearSelected();
    const searchSelectorParams = getSearchSelectorParams(searchValue.value);
    const params = {
      spec_cluster_type: props.dbType,
      spec_machine_type: props.machineType,
      ...searchSelectorParams,
    };
    if (isEnableSpec.value) {
      Object.assign(params, { enable: isEnableSpec.value });
    }

    tableRef.value.fetchData({ ...params });
    if (isShowReplenish) {
      fetchRadioMap();
    }
  };

  const handleSelectionChange = (_idList: string[], list: ResourceSpecModel[]) => {
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
    clearSearchValue();
  };

  const handleBacthDelete = () => {
    handleDelete(selectedList.value);
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

    .resource-spec-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 16px;

      .batch-operation {
        .batch-operation-icon {
          transform: rotate(0);
          transition: all 0.2s;
        }

        .batch-operation-icon-active {
          transform: rotate(180deg);
        }
      }

      .enable-checkbox {
        display: flex;
        margin-right: 16px;
        margin-left: auto;
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
