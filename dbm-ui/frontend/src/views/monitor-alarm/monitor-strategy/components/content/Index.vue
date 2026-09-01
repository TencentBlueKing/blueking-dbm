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
  <ApplyPermissionCatch>
    <BkAlert
      closable
      :title="
        t(
          '业务策略默认与全局策略保持同步。编辑告警规则后将转为「自定义」，不再跟随全局更新；修改告警组不影响同步关系。如需回退，可通过「恢复默认」还原。',
        )
      " />
    <div class="monitor-strategy-type-content mt-16">
      <div class="content-head mb-16">
        <AuthButton
          action-id="monitor_policy_manage"
          :disabled="!selected.length"
          :resource="dbType"
          theme="primary"
          @click="batchEditNoticeGroup">
          {{ t('批量设置告警组') }}
        </AuthButton>
        <AuthButton
          v-bk-tooltips="{
            content: t('请选择至少一条自定义父策略'),
            disabled: !batchResetToDefaultDisabled,
          }"
          action-id="monitor_policy_manage"
          class="ml-8"
          :disabled="batchResetToDefaultDisabled"
          :resource="dbType"
          theme="primary"
          @click="batchResetToDefault">
          {{ t('批量恢复默认') }}
        </AuthButton>
        <DbQuickSearch
          v-model="searchValue"
          :data="quickSearchData"
          parse-url
          :placeholder="t('请输入或选择条件搜索')"
          style="width: 500px; margin-left: auto"
          @change="handleQuickSearchChange" />
      </div>
      <div
        ref="tableWrapper"
        class="table-box">
        <BkLoading :loading="isLoading">
          <PrimaryTable
            ref="table"
            :bk-ui-settings="settings"
            :data="tableDisplayData"
            :max-height="tableMaxHeight"
            resizable
            :row-class-name="rowClassName"
            row-key="id"
            :selected-row-keys="selectedRowKeys"
            @bk-ui-settings-change="updateTableSettings"
            @select-change="handleSelectChange">
            <template #default>
              <TableColumn
                col-key="row-expand"
                fixed="left"
                :width="40">
                <template #default="{ row, rowIndex }: { row: MonitorPolicyModel, rowIndex: number}">
                  <div class="row-expand-content-box">
                    <DbIcon
                      v-if="!row.isChild && row.child.length > 0"
                      class="row-expand-icon"
                      :class="{ 'row-expand-icon-expanded': expandedRowMap[row.id] }"
                      type="right-shape"
                      @click="() => handleExpandChange(row.id)" />
                    <BkTag
                      v-if="row.isChild"
                      size="small"
                      style="font-weight: bolder"
                      theme="warning">
                      {{ t('子') }}
                    </BkTag>
                  </div>
                  <div class="row-expand-line-box">
                    <div
                      v-if="row.isChild"
                      class="dashed-line-horizontal" />
                    <div
                      v-if="!row.isChild && row.child.length > 0 && expandedRowMap[row.id]"
                      class="dashed-line-vertical-parent" />
                    <div
                      v-if="row.isChild && !isLastChild(row, rowIndex)"
                      class="dashed-line-vertical-child-common" />
                    <div
                      v-if="row.isChild && isLastChild(row, rowIndex)"
                      class="dashed-line-vertical-child-last" />
                  </div>
                </template>
              </TableColumn>
              <TableColumn
                col-key="row-select"
                fixed="left"
                type="multiple"
                :width="40" />
              <!-- <TableColumn
                col-key="id"
                fixed="left"
                title="ID"
                :width="130">
              </TableColumn> -->
              <TableColumn
                col-key="name"
                fixed="left"
                :title="t('策略名称')"
                :width="300">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <div style="display: flex">
                    <TextOverflowLayout>
                      <AuthButton
                        action-id="monitor_policy_manage"
                        :permission="row.permission.monitor_policy_manage"
                        :resource="dbType"
                        text
                        theme="primary"
                        @click="() => handleOpenSlider(row, row.isInnerReal ? 'clone' : 'edit')">
                        {{ row.nameDisplay }}
                      </AuthButton>
                      <template #append>
                        <div class="ml-4" />
                        <BkTag
                          v-if="row.event_count > 0"
                          v-bk-tooltips="{
                            content: t('当前有n个未恢复事件', { n: row.event_count }),
                          }"
                          size="small"
                          style="cursor: pointer"
                          theme="danger"
                          @click="() => handleGoMonitorPage(row.event_url)">
                          <DbIcon type="alert" />
                          {{ row.event_count }}
                        </BkTag>
                        <!-- <BkTag
                          v-if="row.isInner"
                          size="small">
                          {{ t('内置') }}
                        </BkTag> -->
                        <BkTag
                          v-if="row.isCustom"
                          size="small"
                          theme="warning">
                          {{ t('自定义') }}
                        </BkTag>
                        <!-- <BkTag
                          v-if="row.isPolicyTypePromQL"
                          size="small"
                          style="color: #531dab; background: #f9f0ff">
                          PromQL
                        </BkTag> -->
                        <!-- <BkTag
                          v-if="row.isPolicyTypeMulti"
                          size="small"
                          theme="success">
                          {{ t('多指标') }}
                        </BkTag> -->
                        <BkTag
                          v-if="!row.is_enabled"
                          class="ml-4"
                          size="small">
                          {{ t('已停用') }}
                        </BkTag>
                      </template>
                    </TextOverflowLayout>
                  </div>
                </template>
              </TableColumn>
              <TableColumn
                col-key="targets"
                :min-width="300"
                :title="t('监控目标')">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <Targets :row="row" />
                </template>
              </TableColumn>
              <TableColumn
                col-key="is_enabled"
                :title="t('启停')"
                :width="60">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <BkSwitcher
                    v-if="enableButtonDisabled(row)"
                    v-bk-tooltips="{
                      disabled: !enableButtonDisabled(row),
                      content: row.isCustom
                        ? t('父策略为告警兜底，需保持启用以确保告警覆盖')
                        : t('继承自全局策略，启停与全局保持一致'),
                    }"
                    disabled
                    :model-value="row.is_enabled"
                    size="small"
                    theme="primary" />
                  <AuthTemplate
                    v-else-if="getEnablePopConfirmInfo(row).content"
                    action-id="monitor_policy_manage"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType">
                    <BkPopConfirm
                      :content="getEnablePopConfirmInfo(row).content"
                      :is-show="showTipMap[row.id]"
                      placement="bottom"
                      :title="getEnablePopConfirmInfo(row).title"
                      trigger="manual"
                      :width="320"
                      @cancel="() => handleCancelConfirm(row)"
                      @confirm="() => handleClickConfirm(row)">
                      <AuthSwitcher
                        v-model="row.is_enabled"
                        action-id="monitor_policy_manage"
                        :permission="row.permission.monitor_policy_manage"
                        :resource="dbType"
                        size="small"
                        theme="primary"
                        @change="() => handleChangeSwitchPopConfirm(row)" />
                    </BkPopConfirm>
                  </AuthTemplate>
                  <AuthTemplate
                    v-else
                    action-id="monitor_policy_manage"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType">
                    <AuthSwitcher
                      v-model="row.is_enabled"
                      action-id="monitor_policy_manage"
                      :permission="row.permission.monitor_policy_manage"
                      :resource="dbType"
                      size="small"
                      theme="primary"
                      @change="() => handleChangeSwitchCommon(row)" />
                  </AuthTemplate>
                </template>
              </TableColumn>
              <TableColumn
                col-key="test_rules"
                :title="t('阈值')"
                :width="220">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <TestRules :test-rules="row.test_rules" />
                </template>
              </TableColumn>
              <TableColumn
                col-key="trigger_config"
                :title="t('触发条件')"
                :width="100">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  {{ row.detects_config.trigger_config.count }}/{{ row.detects_config.trigger_config.check_window }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="time_ranges"
                :title="t('生效时间段')"
                :width="220">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <template v-if="row.timeRangesDisplay">
                    <BkTag
                      v-if="row.timeRangesDisplay.length === 0"
                      theme="info">
                      {{ t('全天') }}
                    </BkTag>
                    <TagBlock
                      v-else
                      :data="row.timeRangesDisplay" />
                  </template>
                  <span v-else>--</span>
                </template>
              </TableColumn>
              <TableColumn
                col-key="notify_groups"
                :title="t('告警组')"
                :width="240">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <RenderNotifyGroup :data="getNoticeGroupDisplay(row)" />
                </template>
              </TableColumn>
              <TableColumn
                col-key="updater"
                :title="t('更新人')"
                :width="150">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  {{ row.updater || '--' }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="update_at"
                sorter
                :title="t('更新时间')"
                :width="220">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  {{ row.updateAtDisplay }}
                </template>
              </TableColumn>
              <TableColumn
                col-key="oprations"
                fixed="right"
                :title="t('操作')"
                :width="180">
                <template #default="{ row }: { row: MonitorPolicyModel }">
                  <AuthButton
                    action-id="monitor_policy_manage"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType"
                    text
                    theme="primary"
                    @click="() => handleOpenSlider(row, row.isInnerReal ? 'clone' : 'edit')">
                    {{ t('编辑') }}
                  </AuthButton>
                  <AuthButton
                    v-if="!row.isChild"
                    action-id="monitor_policy_manage"
                    class="ml-8"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType"
                    text
                    theme="primary"
                    @click="() => handleOpenSlider(row, 'new')">
                    {{ t('新建子策略') }}
                  </AuthButton>
                  <AuthButton
                    v-if="row.isChild"
                    action-id="monitor_policy_manage"
                    class="ml-8"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType"
                    text
                    theme="primary"
                    @click="() => handleOpenSlider(row, 'clone')">
                    {{ t('克隆') }}
                  </AuthButton>
                  <AuthButton
                    v-if="row.isCustom"
                    action-id="monitor_policy_manage"
                    class="ml-8"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType"
                    text
                    theme="primary"
                    @click="() => handleResetToDefault(row)">
                    {{ t('恢复默认') }}
                  </AuthButton>
                  <AuthButton
                    v-if="row.isChild"
                    action-id="monitor_policy_manage"
                    class="ml-8"
                    :permission="row.permission.monitor_policy_manage"
                    :resource="dbType"
                    text
                    theme="primary"
                    @click="() => handleClickDelete(row)">
                    {{ t('删除') }}
                  </AuthButton>
                </template>
              </TableColumn>
            </template>
          </PrimaryTable>
        </BkLoading>
      </div>
    </div>
    <EditStrategy
      v-model="isShowEditStrrategySideSilder"
      :alarm-group-list="alarmGroupList"
      :alarm-group-name-map="alarmGroupNameMap"
      :app-parent-info-map="appParentInfoMap"
      :cluster-list="clusterList"
      :data="currentChoosedRow"
      :db-type="dbType"
      :existed-names="existedNames"
      :page-status="pageStatus"
      @success="handleUpdatePolicySuccess" />
    <BatchEditNoticeGroupDialog
      v-model="batchEditNoticeGroupDialogShow"
      :alarm-group-list="alarmGroupList"
      :alarm-group-name-map="alarmGroupNameMap"
      :db-type="dbType"
      :selected="selected"
      @suceess="handleBatchEditNoticeGroupSuceess" />
    <BatchResetToDefaultDialog
      v-model="batchResetToDefalutDialogShow"
      :selected="selected"
      @suceess="handleBatchResetToDefaultSuceess" />
  </ApplyPermissionCatch>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { type UnwrapRef } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import {
    clonePolicy,
    deletePolicy,
    disablePolicy,
    enablePolicy,
    getClusterList,
    queryMonitorPolicyList,
    updatePolicy,
  } from '@services/source/monitor';
  import { listGroupName } from '@services/source/monitorNoticeGroup';

  import { useTableSettings, useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { DBTypes, MonitorTargetLevel, UserPersonalSettings } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import AuthButton from '@components/auth-component/button.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import TestRules from '@views/monitor-alarm/common/table/TestRules.vue';
  import { useStrategyQuickSearch } from '@views/monitor-alarm/common/useStrategyQuickSearch';
  import { getDbaLabel } from '@views/monitor-alarm/common/utils';

  import { getOffset, messageSuccess } from '@utils';

  import DbIcon from '@/components/db-icon';

  import EditStrategy from '../edit-strategy/Index.vue';

  import BatchEditNoticeGroupDialog from './components/BatchEditNoticeGroupDialog.vue';
  import BatchResetToDefaultDialog from './components/BatchResetToDefaultDialog.vue';
  import RenderNotifyGroup from './components/RenderNotifyGroup.vue';
  import Targets from './components/table/Targets.vue';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  enum EditType {
    CHILD_EDIT = 'child_edit',
    PARENT_EDIT = 'parent_edit',
    PARENT_NEW = 'parent_new',
  }

  const route = useRoute();
  const router = useRouter();
  const { locale, t } = useI18n();
  const { currentBizId, currentBizInfo } = useGlobalBizs();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const { handleFilterList, handleMergeSearchParams, isSearching, quickSearchData, searchValue } =
    useStrategyQuickSearch(false, props.dbType);
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.MONITOR_STRATEGY_BIZ_SETTINGS, {
    disabled: ['row-expand', 'name'],
  });

  const rootRef = useTemplateRef('tableWrapper');

  let editType = route.query.edit_type || '';

  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as MonitorPolicyModel);
  const alarmGroupList = ref<SelectItem<number>[]>([]);
  const pageStatus = ref<ComponentProps<typeof EditStrategy>['pageStatus']>('edit');
  const clusterList = ref<SelectItem<string>[]>([]);
  const existedNames = ref<string[]>([]);
  const showTipMap = ref<Record<string, boolean>>({});
  const batchEditNoticeGroupDialogShow = ref(false);
  const batchResetToDefalutDialogShow = ref(false);
  const tableMaxHeight = ref<number | 'auto'>('auto');
  const selectedRowKeys = ref<number[]>([]);

  const selected = shallowRef<MonitorPolicyModel[]>([]);
  const tableFilterData = ref<MonitorPolicyModel[]>([]);
  const expandedRowMap = shallowRef({} as Record<number, boolean>);
  const appParentInfoMap = shallowRef({} as Record<number, MonitorPolicyModel>); // 全局策略和业务策略的映射

  const batchResetToDefaultDisabled = computed(() => selected.value.filter((item) => item.isCustom).length === 0);
  const isLoading = computed(
    () =>
      isTableLoading.value ||
      isEnableLoading.value ||
      isDisableLoading.value ||
      isDeleteLoading.value ||
      isCloneLoading.value ||
      isUpdateLoading.value,
  );

  const tableDisplayData = computed(() =>
    tableFilterData.value.flatMap((item) => {
      if (expandedRowMap.value[item.id]) {
        return [item].concat(item.child);
      }
      return item;
    }),
  );

  const alarmGroupNameMap: Record<string, string> = {};
  const { run: fetchAlarmGroupList } = useRequest(listGroupName, {
    manual: true,
    onSuccess: (res) => {
      const groupList: SelectItem<number>[] = [];
      res.forEach((item) => {
        groupList.push({
          label: item.name,
          value: item.id,
        });
        alarmGroupNameMap[item.id] = item.name;
      });
      alarmGroupList.value = groupList;
    },
  });

  const {
    data: tableOriginalData,
    loading: isTableLoading,
    run: runQueryMonitorPolicyList,
  } = useRequest(queryMonitorPolicyList, {
    manual: true,
    onSuccess: (result, params) => {
      if (editType && route.query.id) {
        const row = result.results
          .flatMap((item) => [item].concat(item.child))
          .find((item) => item.id === Number(route.query.id));
        if (row && result) {
          const typeMap: Record<EditType, UnwrapRef<typeof pageStatus>> = {
            [EditType.CHILD_EDIT]: 'edit',
            [EditType.PARENT_EDIT]: 'edit',
            [EditType.PARENT_NEW]: 'new',
          };
          const type = editType === EditType.PARENT_EDIT && row.isInnerReal ? 'clone' : typeMap[editType as EditType];
          handleOpenSlider(row, type);
        }
        editType = '';
      }
      router.replace({
        query: replaceSearchParams(params[0], false),
      });
      expandedRowMap.value = Object.fromEntries(result.results.map((item) => [item.id, true]));

      const globalMap = new Map<number, MonitorPolicyModel>();
      const globalBizMap = new Map<number, MonitorPolicyModel[]>();
      const localAppParentInfoMap = {} as UnwrapRef<typeof appParentInfoMap>;

      for (const res of result.results) {
        const { id, parent_id, target_level } = res;

        if (target_level === MonitorTargetLevel.BIZ) {
          if (!globalBizMap.has(parent_id)) {
            globalBizMap.set(parent_id, []);
          }
          globalBizMap.get(parent_id)!.push(res);
        } else if (target_level === MonitorTargetLevel.PLATFORM) {
          globalMap.set(id, res);
        }
      }
      for (const [parentId, bizMonitorPolicyList] of globalBizMap) {
        bizMonitorPolicyList.forEach((policyItem) => {
          localAppParentInfoMap[policyItem.id] = globalMap.get(parentId)!;
        });
      }

      appParentInfoMap.value = localAppParentInfoMap;

      if (isSearching.value) {
        const filterList = handleFilterList(tableOriginalData.value?.results || []);
        tableFilterData.value = handleFormatTableList(filterList, result.results);
      } else {
        tableFilterData.value = handleFormatTableList(result.results, result.results);
      }
    },
  });

  const { run: fetchClusers } = useRequest(getClusterList, {
    manual: true,
    onSuccess: (res) => {
      clusterList.value = res.map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  const { loading: isGlobalMonitorPolicyLoading, runAsync: runQueryGlobalMonitorPolicy } = useRequest(
    queryMonitorPolicyList,
    {
      manual: true,
    },
  );

  const { loading: isEnableLoading, run: runEnablePolicy } = useRequest(enablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (isEnabled) {
        messageSuccess(t('启用成功'));
        fetchData();
      }
    },
  });

  const { loading: isDisableLoading, run: runDisablePolicy } = useRequest(disablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (!isEnabled) {
        // 停用成功
        messageSuccess(t('停用成功'));
        fetchData();
      }
    },
  });

  const { loading: isDeleteLoading, run: runDeletePolicy } = useRequest(deletePolicy, {
    manual: true,
    onSuccess: (isDeleted) => {
      if (isDeleted === null) {
        // 停用成功
        messageSuccess(t('操作成功'));
        fetchData();
      }
    },
  });

  const { loading: isCloneLoading, run: runClonePolicy } = useRequest(clonePolicy, {
    manual: true,
    onSuccess: (cloneResponse) => {
      if (cloneResponse.bkm_id) {
        messageSuccess(t('启用成功'));
        fetchData();
      }
    },
  });

  const { loading: isUpdateLoading, run: runUpdatePolicy } = useRequest(updatePolicy, {
    manual: true,
    onSuccess: (updateResponse) => {
      if (updateResponse.bkm_id) {
        messageSuccess(t('启用成功'));
        fetchData();
      }
    },
  });

  watch(
    () => props.dbType,
    (type) => {
      if (type) {
        fetchClusers({
          bk_biz_id: currentBizId,
          dbtype: type,
        });
        fetchAlarmGroupList({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          db_type: type,
        });
      }
    },
    {
      immediate: true,
    },
  );

  // 全局启用，启停按钮禁用
  const enableButtonDisabled = (row: MonitorPolicyModel) => {
    return (
      (row.isInnerReal && row.is_enabled) ||
      ((row.isInnerFake || row.isCustom) && appParentInfoMap.value[row.id].is_enabled)
    );
  };

  const getEnablePopConfirmInfo = (row: MonitorPolicyModel) => {
    // 全局已禁用，启用当前策略（从继承变为自定义）
    if ((row.isInnerReal && !row.is_enabled) || (row.isInnerFake && !appParentInfoMap.value[row.id].is_enabled)) {
      return {
        content: t('启用后，该策略将转为自定义管理，不再跟随全局策略更新。'),
        title: t('确认启用该策略？'),
      };
    }
    // 全局已禁用，停用当前策略（已是自定义）
    if (row.isCustom && !appParentInfoMap.value[row.id].is_enabled && row.is_enabled) {
      return {
        content: t('停用后，不匹配子策略的对象将失去该告警覆盖。'),
        title: t('确认停用该策略？'),
      };
    }
    if (row.isChild && row.is_enabled) {
      return {
        content: t('停用后，该子策略覆盖的对象将回退使用父策略的告警规则。'),
        title: t('确认停用该子策略？'),
      };
    }
    return {
      content: '',
      title: '',
    };
  };

  const handleFormatTableList = (filterData: MonitorPolicyModel[], allData: MonitorPolicyModel[]) => {
    // 父类id既全局策略id
    const parentIds = new Set<number>();
    // 业务策略id
    const appIds = new Set<number>();
    // 除业务和全局策略之外的id
    const childIds: number[] = [];
    // 全局策略和业务策略的映射
    const parentAppMap = new Map<number, number[]>();
    // 全局策略和子策略的映射
    const parentChildMap = new Map<number, number[]>();
    // 最后的父策略和子策略的映射
    const lastParentChildMap = new Map<number, number[]>();

    for (const res of filterData) {
      const { id, parent_id, target_level } = res;
      parentIds.add(parent_id === 0 ? id : parent_id);

      // 全局策略可以跳过，不需要记录父策略和子策略的关系
      if (parent_id === 0) {
        continue;
      }

      if (target_level === MonitorTargetLevel.BIZ) {
        appIds.add(id);
        if (!parentAppMap.has(parent_id)) {
          parentAppMap.set(parent_id, []);
        }
        parentAppMap.get(parent_id)!.push(id);
      } else if (target_level !== MonitorTargetLevel.PLATFORM) {
        childIds.push(id);
        if (!parentChildMap.has(parent_id)) {
          parentChildMap.set(parent_id, []);
        }
        parentChildMap.get(parent_id)!.push(id);
      }
    }

    // 拿到未查到的业务策略，用来覆盖全局策略
    const missingParentIds = Array.from(parentChildMap.keys()).filter((pid) => !parentAppMap.has(pid));

    const bizPolicies = allData
      .filter(
        (item) =>
          item.bk_biz_id === currentBizId &&
          missingParentIds.includes(item.parent_id) &&
          item.target_level === MonitorTargetLevel.BIZ,
      )
      .map((item) => ({
        id: item.id,
        parent_id: item.parent_id,
      }));

    const bizPolicyMap = new Map<number, number>();
    bizPolicies.forEach((p: any) => {
      bizPolicyMap.set(p.parent_id, p.id);
    });

    for (const parentId of Array.from(parentChildMap.keys())) {
      // 当又有全局策略又有业务策略时，不返回全局策略
      if (parentAppMap.has(parentId)) {
        // 可能会存在一个全局策略有多个业务策略的非标行为，所以取第一个就行
        const lastParentId = parentAppMap.get(parentId)![0];
        lastParentChildMap.set(lastParentId, parentChildMap.get(parentId)!);
        appIds.delete(lastParentId);
      }
      // 如果没拿到对应的业务策略则需要获取全局策略对应的业务策略
      else if (bizPolicyMap.has(parentId)) {
        lastParentChildMap.set(bizPolicyMap.get(parentId)!, parentChildMap.get(parentId)!);
      } else {
        lastParentChildMap.set(parentId, parentChildMap.get(parentId)!);
      }
      parentIds.delete(parentId);
    }

    // 最后再把存在业务策略的全局策略去掉
    for (const parentId of Array.from(parentAppMap.keys())) {
      if (parentIds.has(parentId)) {
        parentIds.delete(parentId);
      }
    }

    const firstLevelIds = [...Array.from(parentIds), ...Array.from(appIds), ...Array.from(lastParentChildMap.keys())];

    // 拿到所有的需要查询的策略的id
    const needIds = [...firstLevelIds, ...childIds];
    const resData = allData.filter((item) => needIds.includes(item.id));
    const results: MonitorPolicyModel[] = [];

    const getChildData = (allData: any[], ids: number[]) => {
      return allData.filter((data) => ids.includes(data.id));
    };

    for (const res of resData) {
      if (firstLevelIds.includes(res.id)) {
        res.child = lastParentChildMap.has(res.id) ? getChildData(resData, lastParentChildMap.get(res.id)!) : [];
        results.push(res);
      }
    }

    // TODO 后续改为自然排序
    const sortedResults = [...results].sort((a, b) => {
      return a.nameDisplay.localeCompare(b.nameDisplay, locale.value, {
        numeric: true,
        sensitivity: 'base',
      });
    });

    sortedResults.forEach((parent: MonitorPolicyModel) => {
      if (parent.child && parent.child.length > 0) {
        parent.child.sort((a: MonitorPolicyModel, b: MonitorPolicyModel) => {
          return dayjs(b.create_at).valueOf() - dayjs(a.create_at).valueOf();
        });
      }
    });

    return sortedResults;
  };

  const fetchData = () => {
    runQueryMonitorPolicyList(
      {
        bk_biz_id: currentBizId,
        db_type: props.dbType,
        limit: -1,
        offset: 0,
      },
      {
        permission: 'catch',
      },
    );
  };

  const handleQuickSearchChange = () => {
    const filterList = handleFilterList(tableOriginalData.value?.results || []);
    router.replace({
      query: replaceSearchParams(handleMergeSearchParams(getSearchParams()), false),
    });
    tableFilterData.value = handleFormatTableList(filterList, tableOriginalData.value?.results || []);
  };

  const handleExpandChange = (id: number) => {
    const isExpended = expandedRowMap.value[id];
    expandedRowMap.value = { ...expandedRowMap.value, [id]: !isExpended };
  };

  const isLastChild = (row: MonitorPolicyModel, rowIndex: number) => {
    const parentRow = _.findLast(tableDisplayData.value, (item) => item.child.length > 0, rowIndex)!;
    const childIndex = parentRow.child.findIndex((item) => item.id === row.id);
    return childIndex === parentRow.child.length - 1;
  };

  const rowClassName = ({ row, rowIndex }: { row: MonitorPolicyModel; rowIndex: number }) => {
    const classList: string[] = [];
    if (
      (!row.isChild && row.child.length > 0 && expandedRowMap.value[row.id]) ||
      (row.isChild && !isLastChild(row, rowIndex))
    ) {
      classList.push('expanded-row');
    }
    if (row.isChild) {
      classList.push('child-row');
    }
    return classList.join(' ');
  };

  const getNoticeGroupDisplay = (row: MonitorPolicyModel) => {
    if (row.notify_groups.length === 0) {
      return [
        {
          displayName: getDbaLabel(props.dbType),
          id: props.dbType,
        },
      ];
    }

    const dataList: {
      displayName: string;
      id: string;
    }[] = [];
    row.notify_groups.forEach((id) => {
      if (id in alarmGroupNameMap) {
        dataList.push({
          displayName: alarmGroupNameMap[id],
          id: `${id}`,
        });
      }
    });
    return dataList;
  };

  const handleSelectChange = (value: (string | number)[], { selectedRowData }: { selectedRowData: unknown[] }) => {
    selectedRowKeys.value = value as number[];
    selected.value = selectedRowData as MonitorPolicyModel[];
  };

  const batchEditNoticeGroup = () => {
    batchEditNoticeGroupDialogShow.value = true;
  };

  const batchResetToDefault = () => {
    batchResetToDefalutDialogShow.value = true;
  };

  const handleGoMonitorPage = (url: string) => {
    window.open(url);
  };

  const handleClickDelete = (row: MonitorPolicyModel) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定删除'),
      contentAlign: 'left',
      infoType: 'danger',
      onConfirm: () => {
        runDeletePolicy({ id: row.id });
      },
      subTitle: (
        <>
          <div class='mb-16'>
            {t('策略名称：')}
            {row.nameDisplay}
          </div>
          <div style='padding: 12px 16px; background: #F5F7FA; color: #4D4F56'>
            {t('删除子策略后，原先匹配该子策略条件的对象将回退到父策略的告警配置.')}
          </div>
        </>
      ),
      title: t('确认删除子策略？'),
    });
  };

  const handleResetToDefault = (row: MonitorPolicyModel) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定恢复'),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: () => {
        runDeletePolicy({ id: row.id });
      },
      subTitle: (
        <>
          <div class='mb-16'>
            {t('策略名称：')}
            {row.nameDisplay}
          </div>
          <div style='padding: 12px 16px; background: #F5F7FA; color: #4D4F56'>
            {t('恢复默认将覆盖当前所有自定义修改，恢复为全局策略配置。此操作不可撤销。')}
          </div>
        </>
      ),
      title: t('确认恢复为默认？'),
    });
  };

  // getEnablePopConfirmInfo 中的 case
  const handleChangeSwitchPopConfirm = (row: MonitorPolicyModel) => {
    Object.assign(row, {
      is_enabled: !row.is_enabled,
    });

    if (isGlobalMonitorPolicyLoading.value) {
      return;
    }

    if (row.isChild) {
      showTipMap.value[row.id] = true;
      return;
    }

    // 预检测对应全局策略的最新数据，对比更新时间
    runQueryGlobalMonitorPolicy({
      bk_biz_id: 0,
      db_type: props.dbType,
      id: row.isInnerReal ? row.id : row.parent_id,
      limit: -1,
      offset: 0,
    }).then((res) => {
      const getGlobalPolicyList = res.results;
      if (getGlobalPolicyList.length > 0) {
        const [globalPolicy] = getGlobalPolicyList;
        const updateAt = dayjs(row.isInnerReal ? row.update_at : appParentInfoMap.value[row.id].update_at);
        if (dayjs(globalPolicy.update_at).isAfter(updateAt)) {
          InfoBox({
            confirmText: t('刷新页面'),
            infoType: 'warning',
            onConfirm: () => {
              window.location.reload();
            },
            subTitle: t('全局策略已变更，当前页面数据已过期，请刷新后重试。'),
            title: '',
          });
          return;
        }
      }

      showTipMap.value[row.id] = true;
    });
  };

  // 根据 getEnablePopConfirmInfo 中的 case 来判断
  const handleClickConfirm = (row: MonitorPolicyModel) => {
    const getBizDefaultGroupIds = () => {
      const groupItem = alarmGroupList.value.find((item) => item.label === getDbaLabel(props.dbType));
      return groupItem ? [Number(groupItem.value)] : [];
    };

    if (row.isInnerReal || row.isInnerFake) {
      // 全局已禁用，启用当前策略（从继承变为自定义）
      if (row.isInnerFake) {
        runUpdatePolicy(row.id, {
          agg_info: row.agg_info,
          custom_conditions: row.custom_conditions,
          detects_config: row.detects_config,
          get_data_time: appParentInfoMap.value[row.id].update_at,
          is_enabled: true,
          no_data_config: row.no_data_config,
          notify_config: row.notify_config,
          notify_groups: row.notify_groups,
          notify_rules: row.notify_rules,
          policy_tag: 'custom' as const,
          targets: row.targets,
          test_rules: row.test_rules,
        });
      } else {
        // 真内置转为自定义，需要克隆
        runClonePolicy({
          agg_info: row.agg_info,
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          custom_conditions: row.custom_conditions,
          detects_config: row.detects_config,
          get_data_time: row.update_at,
          is_enabled: true,
          name: MonitorPolicyModel.FormatFinalName(row.nameDisplay, currentBizInfo),
          no_data_config: row.no_data_config,
          notify_config: row.notify_config,
          notify_groups: getBizDefaultGroupIds(),
          notify_rules: row.notify_rules,
          parent_id: row.id,
          policy_tag: 'custom' as const,
          targets: [
            {
              level: MonitorTargetLevel.BIZ,
              rule: {
                key: MonitorTargetLevel.BIZ,
                method: row.isPolicyTypePromQL ? '=' : 'eq',
                value: [`${currentBizId}`],
              },
            },
          ],
          test_rules: row.test_rules,
        });
      }
    } else if (row.isCustom) {
      // 全局已禁用，停用当前策略（已是自定义）
      runDisablePolicy({ get_data_time: appParentInfoMap.value[row.id].update_at, id: row.id });
    } else if (row.isChild) {
      // 子策略停用
      runDisablePolicy({ id: row.id });
    }
    showTipMap.value[row.id] = false;
  };

  const handleCancelConfirm = (row: MonitorPolicyModel) => {
    showTipMap.value[row.id] = false;
  };

  // 自定义（已停用）或 子策略启用
  const handleChangeSwitchCommon = (row: MonitorPolicyModel) => {
    if (row.is_enabled) {
      runEnablePolicy({ id: row.id });
    } else {
      runDisablePolicy({ id: row.id });
    }
  };

  const handleOpenSliderCallback = (row: MonitorPolicyModel, type: UnwrapRef<typeof pageStatus>) => {
    existedNames.value = tableOriginalData.value!.results.flatMap((item) =>
      [item.name].concat(item.child.map((childItem) => childItem.name)),
    );
    pageStatus.value = type;
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

  const handleOpenSlider = (row: MonitorPolicyModel, type: UnwrapRef<typeof pageStatus>) => {
    if (isGlobalMonitorPolicyLoading.value) {
      return;
    }

    if (row.isInnerReal || row.isInnerFake || (row.isCustom && type === 'edit')) {
      // 预检测对应全局策略的最新数据，对比更新时间
      runQueryGlobalMonitorPolicy({
        bk_biz_id: 0,
        db_type: props.dbType,
        id: row.isInnerReal ? row.id : row.parent_id,
        limit: -1,
        offset: 0,
      }).then((res) => {
        const getGlobalPolicyList = res.results;
        if (getGlobalPolicyList.length > 0) {
          const [globalPolicy] = getGlobalPolicyList;
          const updateAt = dayjs(row.isInnerReal ? row.update_at : appParentInfoMap.value[row.id].update_at);
          if (dayjs(globalPolicy.update_at).isAfter(updateAt)) {
            InfoBox({
              confirmText: t('刷新页面'),
              infoType: 'warning',
              onConfirm: () => {
                window.location.reload();
              },
              subTitle: t('全局策略已变更，当前页面数据已过期，请刷新后重试。'),
              title: '',
            });
            return;
          }
        }

        handleOpenSliderCallback(row, type);
      });
    } else {
      handleOpenSliderCallback(row, type);
    }
  };

  const handleUpdatePolicySuccess = () => {
    fetchData();
  };

  const handleBatchEditNoticeGroupSuceess = () => {
    selectedRowKeys.value = [];
    selected.value = [];
    fetchData();
  };

  const handleBatchResetToDefaultSuceess = () => {
    selectedRowKeys.value = [];
    selected.value = [];
    fetchData();
  };

  onMounted(() => {
    fetchData();

    setTimeout(() => {
      tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 16;
    });
  });
</script>
<style lang="less">
  .monitor-strategy-type-content {
    display: flex;
    flex-direction: column;

    .content-head {
      display: flex;

      .input-box {
        width: 600px;
        height: 32px;
        margin-left: auto;
      }
    }

    .table-box {
      .expanded-row {
        .t-table__td-first-col {
          border-bottom: none;
        }
      }

      .child-row {
        .t-table__cell-check {
          &::before {
            position: absolute;
            top: 50%;
            left: 0;
            z-index: -1;
            width: 11px;
            border-top: 1px dashed #dcdee5;
            content: '';
            transform: translateY(-50%);
          }
        }
      }

      .row-expand-content-box {
        text-align: center;

        .row-expand-icon {
          display: inline-block;
          font-size: 16px;
          color: #c4c6cc;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.38, 0, 0.24, 1) 0s;
        }

        .row-expand-icon-expanded {
          transform: rotate(90deg);
        }
      }

      .row-expand-line-box {
        .dashed-line-horizontal {
          position: absolute;
          top: 50%;
          right: 0;
          z-index: -1;
          width: 11px;
          border-top: 1px dashed #dcdee5;
          transform: translateY(-50%);
        }

        .dashed-line-vertical-parent {
          position: absolute;
          bottom: 0;
          left: 50%;
          z-index: -1;
          height: 50%;
          border-left: 1px dashed #dcdee5;
          transform: translateX(-50%);
        }

        .dashed-line-vertical-child-common {
          position: absolute;
          top: 0;
          left: 50%;
          z-index: -1;
          height: 100%;
          border-left: 1px dashed #dcdee5;
          transform: translateX(-50%);
        }

        .dashed-line-vertical-child-last {
          position: absolute;
          top: 0;
          left: 50%;
          z-index: -1;
          height: 50%;
          border-left: 1px dashed #dcdee5;
          transform: translateX(-50%);
        }
      }
    }
  }
</style>
