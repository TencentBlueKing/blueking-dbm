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
    <div class="global-strategy-type-content">
      <BkAlert
        class="mb-16"
        closable
        :title="t('修改全局策略将自动同步至所有业务（已自定义的业务策略不受影响）。')" />
      <DbQuickSearch
        v-model="searchValue"
        class="mb-16"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
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
            row-key="id"
            @bk-ui-settings-change="updateTableSettings">
            <TableColumn
              col-key="id"
              fixed="left"
              title="ID"
              :width="130">
            </TableColumn>
            <TableColumn
              col-key="name"
              fixed="left"
              :min-width="300"
              :title="t('策略名称')">
              <template #default="{ row }: { row: MonitorPolicyModel }">
                <TextOverflowLayout>
                  <AuthButton
                    action-id="global_monitor_policy_manage"
                    class="mr-4"
                    :permission="row.permission.global_monitor_policy_manage"
                    :resource="row.id"
                    text
                    theme="primary"
                    @click="() => handleEdit(row)">
                    {{ row.name }}
                  </AuthButton>
                  <!-- <template #append>
                    <div class="ml-4"></div>
                    <BkTag
                      v-if="row.isPolicyTypePromQL"
                      size="small"
                      style="color: #531dab; background: #f9f0ff">
                      PromQL
                    </BkTag>
                    <BkTag
                      v-if="row.isPolicyTypeMulti"
                      size="small"
                      theme="success">
                      {{ t('多指标') }}
                    </BkTag>
                  </template> -->
                </TextOverflowLayout>
              </template>
            </TableColumn>

            <TableColumn
              col-key="is_enabled"
              :title="t('启停')"
              :width="60">
              <template #default="{ row }: { row: MonitorPolicyModel }">
                <BkPopConfirm
                  :content="t('停用后，所有的业务将会停用该策略，请谨慎操作！')"
                  :is-show="showSwitchEnableTipMap[row.id]"
                  placement="bottom"
                  :popover-options="{
                    disabled: !row.is_enabled,
                  }"
                  :title="t('确认停用该策略？')"
                  trigger="click"
                  width="320"
                  @cancel="() => handleSwitchEnableCancelConfirm(row)"
                  @confirm="() => handleSwitchEnableClickConfirm(row)">
                  <AuthSwitcher
                    v-model="row.is_enabled"
                    action-id="global_monitor_policy_manage"
                    :permission="row.permission.global_monitor_policy_manage"
                    :resource="row.id"
                    size="small"
                    theme="primary"
                    @change="() => handleChangeSwitch(row)" />
                </BkPopConfirm>
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
              :width="80">
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
              :title="t('通知对象')"
              :width="180">
              <template #default>
                <span class="notify-box">
                  <DbIcon
                    style="font-size: 16px; color: #979ba5"
                    type="yonghuzu" />
                  <span class="dba">{{ '{' + getDbaLabel(props.dbType) + '}' }}</span>
                </span>
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
              :width="120">
              <template #default="{ row }: { row: MonitorPolicyModel }">
                <AuthButton
                  action-id="global_monitor_policy_manage"
                  :permission="row.permission.global_monitor_policy_manage"
                  :resource="row.id"
                  text
                  theme="primary"
                  @click="() => handleEdit(row)">
                  {{ t('编辑') }}
                </AuthButton>
                <AuthButton
                  action-id="global_monitor_policy_manage"
                  class="ml-8"
                  :permission="row.permission.global_monitor_policy_manage"
                  :resource="row.id"
                  text
                  theme="primary"
                  @click="() => handleResetClickConfirm(row)">
                  {{ t('恢复初始值') }}
                </AuthButton>
              </template>
            </TableColumn>
          </PrimaryTable>
        </BkLoading>
      </div>
    </div>
    <EditStrategy
      v-model="isShowEditStrrategySideSilder"
      :data="currentChoosedRow"
      :db-type="dbType"
      @success="handleEditRuleSuccess" />
  </ApplyPermissionCatch>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { disablePolicy, enablePolicy, queryMonitorPolicyList, resetGlobalStrategy } from '@services/source/monitor';

  import { useTableSettings, useUrlSearch } from '@hooks';

  import { DBTypes, UserPersonalSettings } from '@common/const';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import TestRules from '@views/monitor-alarm/common/table/TestRules.vue';
  import { useStrategyQuickSearch } from '@views/monitor-alarm/common/useStrategyQuickSearch';
  import { getDbaLabel } from '@views/monitor-alarm/common/utils';

  import { getOffset, messageSuccess } from '@utils';

  import EditStrategy from '../edit-strategy/Index.vue';

  interface Props {
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { locale, t } = useI18n();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const { handleFilterList, handleMergeSearchParams, quickSearchData, searchValue } = useStrategyQuickSearch(
    true,
    props.dbType,
  );
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.MONITOR_STRATEGY_GLOBAL_SETTINGS, {
    disabled: ['name'],
  });

  const rootRef = useTemplateRef('tableWrapper');

  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as MonitorPolicyModel);
  const showSwitchEnableTipMap = ref<Record<string, boolean>>({});
  const tableMaxHeight = ref<number | 'auto'>('auto');

  const tableDisplayData = shallowRef<MonitorPolicyModel[]>();

  const isLoading = computed(
    () => isTableLoading.value || isEnableLoading.value || isDisableLoading.value || isResetLoading.value,
  );

  const {
    data: tableOriginalData,
    loading: isTableLoading,
    run: runQueryMonitorPolicyList,
  } = useRequest(queryMonitorPolicyList, {
    manual: true,
    onSuccess(data, params) {
      router.replace({
        query: replaceSearchParams(params[0], false),
      });
      tableDisplayData.value = sortList(data.results);
    },
  });

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

  const { loading: isResetLoading, run: runResetGlobalStrategy } = useRequest(resetGlobalStrategy, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('恢复初始值成功'));
      fetchData();
    },
  });

  const sortList = (results: MonitorPolicyModel[]) => {
    // TODO 后续改为自然排序
    const sortedResults = [...results].sort((a, b) => {
      return a.name.localeCompare(b.name, locale.value, {
        numeric: true,
        sensitivity: 'base',
      });
    });
    return sortedResults;
  };

  const handleQuickSearchChange = () => {
    const results = handleFilterList(tableOriginalData.value?.results || []);
    tableDisplayData.value = sortList(results);

    router.replace({
      query: replaceSearchParams(handleMergeSearchParams(getSearchParams()), false),
    });
  };

  const fetchData = () => {
    runQueryMonitorPolicyList(
      {
        bk_biz_id: 0,
        db_type: props.dbType,
        limit: -1,
        offset: 0,
        // ...searchValue.value,
      },
      {
        permission: 'catch',
      },
    );
  };
  const handleChangeSwitch = (row: MonitorPolicyModel) => {
    if (!row.is_enabled) {
      showSwitchEnableTipMap.value[row.id] = true;
      Object.assign(row, {
        is_enabled: !row.is_enabled,
      });
    } else {
      // 启用
      runEnablePolicy({ id: row.id });
    }
  };

  const handleSwitchEnableClickConfirm = (row: MonitorPolicyModel) => {
    runDisablePolicy({ id: row.id });
    showSwitchEnableTipMap.value[row.id] = false;
  };

  const handleSwitchEnableCancelConfirm = (row: MonitorPolicyModel) => {
    showSwitchEnableTipMap.value[row.id] = false;
  };

  const handleResetClickConfirm = (row: MonitorPolicyModel) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确定恢复'),
      contentAlign: 'left',
      infoType: 'warning',
      onConfirm: () => {
        runResetGlobalStrategy({ policy_id: row.id });
      },
      subTitle: (
        <div style='padding: 12px 16px; background: #F5F7FA; color: #4D4F56'>
          {t('恢复后将还原为平台预设的初始配置，并自动同步至所有业务（已自定义的业务策略不受影响）。')}
        </div>
      ),
      title: t('确认恢复初始值？'),
    });
  };

  const handleEdit = (row: MonitorPolicyModel) => {
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

  const handleEditRuleSuccess = () => {
    fetchData();
    window.changeConfirm = false;
  };

  onMounted(() => {
    fetchData();

    setTimeout(() => {
      tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 24;
    });
  });
</script>

<style lang="less" scoped>
  .global-strategy-type-content {
    display: flex;
    flex-direction: column;

    .input-box {
      width: 600px;
      height: 32px;
      margin-bottom: 16px;
    }

    :deep(.table-box) {
      .strategy-title {
        display: flex;

        .name {
          margin-left: 8px;
        }
      }

      .notify-box {
        display: inline-block;
        height: 22px;
        padding: 2.5px 5px;
        background: #f0f1f5;
        border-radius: 2px;

        .dba {
          margin-left: 8px;
        }
      }

      .operate-box {
        display: flex;
        align-items: center;
      }

      .is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }
    }
  }
</style>
