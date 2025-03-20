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
    <div class="monitor-strategy-type-content">
      <div class="content-head mb-16">
        <BkButton
          :disabled="!selected.length"
          theme="primary"
          @click="batchEditNoticeGroup">
          {{ t('批量设置告警组') }}
        </BkButton>
        <BkSearchSelect
          v-model="searchValue"
          class="input-box"
          :data="searchSelectList"
          :placeholder="t('请选择条件搜索')"
          unique-select
          value-split-code="+"
          @search="fetchData" />
      </div>
      <DbTable
        ref="table"
        class="table-box"
        :columns="columns"
        :data-source="dataSource"
        :disable-select-method="disableSelectMethod"
        :row-class="updateRowClass"
        selectable
        :show-overflow="false"
        :show-settings="false"
        @clear-search="handleClearSearch"
        @selection="handleSelection" />
    </div>
    <EditStrategy
      v-model="isShowEditStrrategySideSilder"
      :alarm-group-list="alarmGroupList"
      :alarm-group-name-map="alarmGroupNameMap"
      :bizs-map="bizsMap"
      :cluster-list="clusterList"
      :data="currentChoosedRow"
      :db-type="activeDbType"
      :existed-names="existedNames"
      :module-list="moduleList"
      :page-status="sliderPageType"
      @success="handleUpdatePolicySuccess" />
    <BatchEditNoticeGroupDialog
      v-model="batchEditNoticeGroupDialogShow"
      :alarm-group-list="alarmGroupList"
      :alarm-group-name-map="alarmGroupNameMap"
      :selected="selected"
      @suceess="handleBatchEditNoticeGroupSuceess" />
  </ApplyPermissionCatch>
</template>
<script setup lang="tsx">
  import { Button, InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import {
    deletePolicy,
    disablePolicy,
    enablePolicy,
    getClusterList,
    getDbModuleList,
    queryMonitorPolicyList,
  } from '@services/source/monitor';
  import { getSimpleList } from '@services/source/monitorNoticeGroup';

  import { useGlobalBizs } from '@stores';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import AuthButton from '@components/auth-component/button.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import EditStrategy from '../edit-strategy/Index.vue';

  import BatchEditNoticeGroupDialog from './components/BatchEditNoticeGroupDialog.vue';
  import RenderNotifyGroup from './components/RenderNotifyGroup.vue';
  import RenderTargetItem from './components/RenderTargetItem.vue';

  export type RowData = ServiceReturnType<typeof queryMonitorPolicyList>['results'][0];

  interface Props {
    activeDbType: string;
  }

  interface SearchSelectItem {
    id: string;
    name: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { bizs, currentBizId } = useGlobalBizs();
  const { notifyGroupId } = useRoute().query as { notifyGroupId: string };
  const tableRef = useTemplateRef('table');

  const dataSource = (params: ServiceParameters<typeof queryMonitorPolicyList>) =>
    queryMonitorPolicyList(
      Object.assign(params, {
        db_type: props.activeDbType,
      }),
      {
        permission: 'catch',
      },
    );

  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as MonitorPolicyModel);
  const searchValue = ref<Array<{ values: SearchSelectItem[] } & SearchSelectItem>>([]);
  const alarmGroupList = ref<SelectItem<string>[]>([]);
  const sliderPageType = ref('edit');
  const moduleList = ref<SelectItem<string>[]>([]);
  const clusterList = ref<SelectItem<string>[]>([]);
  const isTableLoading = ref(false);
  const existedNames = ref<string[]>([]);
  const showTipMap = ref<Record<string, boolean>>({});
  const batchEditNoticeGroupDialogShow = ref(false);

  const selected = shallowRef<MonitorPolicyModel[]>([]);

  async function fetchData() {
    isTableLoading.value = true;
    try {
      await tableRef.value!.fetchData(
        { ...reqParams.value },
        {
          bk_biz_id: currentBizId,
          db_type: props.activeDbType,
        },
      );
    } finally {
      isTableLoading.value = false;
    }
  }

  const bizsMap = computed(() =>
    bizs.reduce(
      (results, item) => {
        // eslint-disable-next-line no-param-reassign
        results[item.bk_biz_id] = item.name;
        return results;
      },
      {} as Record<string, string>,
    ),
  );

  const searchSelectList = computed(() => [
    {
      id: 'name',
      name: t('策略名称'),
    },
    {
      id: 'target_keyword',
      name: t('监控目标'),
    },
    {
      children: alarmGroupList.value.map((item) => ({
        id: String(item.value),
        name: item.label,
      })) as SearchSelectItem[],
      id: 'notify_groups',
      multiple: true,
      name: t('告警组'),
    },
    {
      id: 'updater',
      name: t('更新人'),
    },
  ]);

  const reqParams = computed(() => {
    const searchParams = searchValue.value.reduce(
      (obj, item) => {
        Object.assign(obj, {
          [item.id]: item.values.map((data) => data.id).join(','),
        });
        return obj;
      },
      {} as Record<string, string>,
    );
    return {
      ...searchParams,
    };
  });

  const alarmGroupNameMap: Record<string, string> = {};
  const dbModuleMap: Record<string, string> = {};
  const columns = [
    {
      field: 'name',
      fixed: 'left',
      label: t('策略名称'),
      minWidth: 150,
      render: ({ data }: { data: MonitorPolicyModel }) => {
        const isDanger = data.event_count > 0;
        const pageType = data.isInner ? 'read' : 'edit';
        const ButtonCom = data.isInner ? Button : AuthButton;
        return (
          <TextOverflowLayout>
            {{
              append: () => (
                <>
                  {data.isInner && (
                    <bk-tag
                      class='ml-4'
                      size='small'>
                      {t('内置')}
                    </bk-tag>
                  )}
                  {!data.is_enabled && (
                    <bk-tag
                      class='ml-4'
                      size='small'>
                      {t('已停用')}
                    </bk-tag>
                  )}
                  {isDanger && (
                    <bk-tag
                      v-bk-tooltips={{
                        content: t('当前有n个未恢复事件', { n: data.event_count }),
                      }}
                      class='ml-4'
                      size='small'
                      style='cursor: pointer;'
                      theme='danger'
                      onclick={() => handleGoMonitorPage(data.event_url)}>
                      <db-icon type='alert' />
                      {data.event_count}
                    </bk-tag>
                  )}
                  {data.isNewCreated && (
                    <bk-tag
                      class='ml-4'
                      size='small'
                      theme='success'>
                      NEW
                    </bk-tag>
                  )}
                </>
              ),
              default: () => (
                <ButtonCom
                  actionId='monitor_policy_edit'
                  disabled={!data.is_enabled}
                  permission={data.permission.monitor_policy_edit}
                  resource={data.id}
                  theme='primary'
                  text
                  onClick={() => handleOpenSlider(data, pageType)}>
                  {data.name}
                </ButtonCom>
              ),
            }}
          </TextOverflowLayout>
        );
      },
      width: 280,
    },
    {
      field: 'targets',
      label: t('监控目标'),
      minWidth: 180,
      render: ({ data }: { data: MonitorPolicyModel }) => {
        if (data.targets.length < 1) {
          return '--';
        }
        return data.targets.map((item, index) => {
          const { level } = item;
          let list = item.rule.value;
          if (level === 'appid') {
            // 业务级
            list = [bizsMap.value[list[0]]];
          }
          if (level === 'db_module') {
            // 模块
            list = item.rule.value.map((item) => dbModuleMap[item]);
          }
          return (
            <RenderTargetItem
              key={index}
              data-test={level}
              list={list}
              title={level}
            />
          );
        });
      },
      showOverflow: false,
    },
    {
      field: 'notify_groups',
      label: t('告警组'),
      minWidth: 180,
      render: ({ data }: { data: MonitorPolicyModel }) => {
        if (data.notify_groups.length === 0) {
          return '--';
        }

        const dataList: {
          displayName: string;
          id: string;
        }[] = [];
        data.notify_groups.forEach((id) => {
          if (id in alarmGroupNameMap) {
            dataList.push({
              displayName: alarmGroupNameMap[id],
              id: `${id}`,
            });
          }
        });
        return <RenderNotifyGroup data={dataList} />;
      },
    },
    {
      field: 'is_enabled',
      label: t('启停'),
      minWidth: 60,
      render: ({ data }: { data: MonitorPolicyModel }) => {
        if (data.isInner) {
          return (
            <bk-switcher
              disabled={true}
              model-value={data.is_enabled}
              size='small'
              theme='primary'
            />
          );
        }
        return (
          <bk-pop-confirm
            content={t('停用后所有监控动作将会停止，请谨慎操作！')}
            disabled={data.isInner}
            is-show={showTipMap.value[data.id]}
            placement='bottom'
            title={t('确认停用该策略？')}
            trigger='manual'
            width='320'
            onCancel={() => handleCancelConfirm(data)}
            onConfirm={() => handleClickConfirm(data)}>
            <auth-switcher
              v-model={data.is_enabled}
              action-id='monitor_policy_start_stop'
              disabled={data.isInner}
              permission={data.permission.monitor_policy_start_stop}
              resource={data.id}
              size='small'
              theme='primary'
              onChange={() => handleChangeSwitch(data)}
            />
          </bk-pop-confirm>
        );
      },
      showOverflowTooltip: true,
    },
    {
      field: 'update_at',
      label: t('更新时间'),
      minWidth: 160,
      render: ({ data }: { data: RowData }) => <span>{data.updateAtDisplay}</span>,
      sort: true,
    },
    {
      field: 'updater',
      label: t('更新人'),
      minWidth: 100,
      render: ({ data }: { data: RowData }) => <span>{data.updater || '--'}</span>,
    },
    {
      field: '',
      fixed: 'right',
      label: t('操作'),
      render: ({ data }: { data: MonitorPolicyModel }) => (
        <div class='operate-box'>
          {!data.isInner && (
            <auth-button
              action-id='monitor_policy_edit'
              permission={data.permission.monitor_policy_edit}
              resource={data.id}
              theme='primary'
              text
              onClick={() => handleOpenSlider(data, 'edit')}>
              {t('编辑')}
            </auth-button>
          )}
          <auth-button
            action-id='monitor_policy_clone'
            permission={data.permission.monitor_policy_clone}
            resource={props.activeDbType}
            theme='primary'
            text
            onClick={() => handleOpenSlider(data, 'clone')}>
            {t('克隆')}
          </auth-button>
          <bk-button
            theme='primary'
            text
            onClick={() => handleOpenMonitorAlarmPage(data.event_url)}>
            {t('监控告警')}
          </bk-button>
          <MoreActionExtend>
            {{
              default: () => (
                <>
                  <bk-dropdown-item>
                    <auth-button
                      action-id='monitor_policy_delete'
                      disabled={data.isInner}
                      permission={data.permission.monitor_policy_delete}
                      resource={data.id}
                      results={data.permission.monitor_policy_delete}
                      text
                      onClick={() => handleClickDelete(data)}>
                      {t('删除')}
                    </auth-button>
                  </bk-dropdown-item>
                </>
              ),
            }}
          </MoreActionExtend>
        </div>
      ),
      showOverflow: false,
      width: 220,
    },
  ];

  const { run: fetchAlarmGroupList } = useRequest(getSimpleList, {
    manual: true,
    onSuccess: (res) => {
      const groupList: SelectItem<string>[] = [];
      res.forEach((item) => {
        groupList.push({
          label: item.name,
          value: item.id,
        });
        alarmGroupNameMap[item.id] = item.name;
      });
      alarmGroupList.value = groupList;
      if (notifyGroupId !== undefined) {
        searchValue.value = [
          {
            id: 'notify_groups',
            name: t('告警组'),
            values: [
              {
                id: notifyGroupId,
                name: alarmGroupNameMap[notifyGroupId],
              },
            ],
          },
        ];
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

  const { run: fetchDbModuleList } = useRequest(getDbModuleList, {
    manual: true,
    onSuccess: (res) => {
      moduleList.value = res.map((item) => {
        dbModuleMap[item.db_module_id] = item.db_module_name;
        return {
          label: item.db_module_name,
          value: String(item.db_module_id),
        };
      });
    },
  });

  const { run: runEnablePolicy } = useRequest(enablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (isEnabled) {
        messageSuccess(t('启用成功'));
        fetchData();
      }
    },
  });

  const { run: runDisablePolicy } = useRequest(disablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (!isEnabled) {
        // 停用成功
        messageSuccess(t('停用成功'));
        fetchData();
      }
    },
  });

  const { run: runDeletePolicy } = useRequest(deletePolicy, {
    manual: true,
    onSuccess: (isDeleted) => {
      if (isDeleted === null) {
        // 停用成功
        messageSuccess(t('删除成功'));
        fetchData();
      }
    },
  });

  watch(
    reqParams,
    () => {
      setTimeout(() => {
        if (tableRef.value) {
          fetchData();
        }
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    () => props.activeDbType,
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
        fetchDbModuleList({
          bk_biz_id: currentBizId,
          dbtype: type,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const disableSelectMethod = (data: MonitorPolicyModel) => data.isInner;

  const handleSelection = (key: number[], list: MonitorPolicyModel[]) => {
    selected.value = list;
  };

  const batchEditNoticeGroup = () => {
    batchEditNoticeGroupDialogShow.value = true;
  };

  const handleClearSearch = () => {
    searchValue.value = [];
  };

  const handleGoMonitorPage = (url: string) => {
    window.open(url);
  };

  const updateRowClass = (row: MonitorPolicyModel) => (row.isNewCreated ? 'is-new' : '');

  const handleClickDelete = (data: MonitorPolicyModel) => {
    InfoBox({
      infoType: 'warning',
      onConfirm: () => {
        runDeletePolicy({ id: data.id });
      },
      subTitle: t('将会删除所有内容，请谨慎操作！'),
      title: t('确认删除该策略？'),
      width: 400,
    });
  };

  const handleChangeSwitch = (row: MonitorPolicyModel) => {
    if (!row.is_enabled) {
      showTipMap.value[row.id] = true;
      Object.assign(row, {
        is_enabled: !row.is_enabled,
      });
    } else {
      // 启用
      runEnablePolicy({ id: row.id });
    }
  };

  const handleClickConfirm = (row: MonitorPolicyModel) => {
    runDisablePolicy({ id: row.id });
    showTipMap.value[row.id] = false;
  };

  const handleCancelConfirm = (row: MonitorPolicyModel) => {
    showTipMap.value[row.id] = false;
  };

  const handleOpenSlider = (row: MonitorPolicyModel, type: string) => {
    existedNames.value = tableRef.value!.getData<MonitorPolicyModel>().map((item) => item.name);
    sliderPageType.value = type;
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

  const handleOpenMonitorAlarmPage = (url: string) => {
    window.open(url, '_blank');
  };

  const handleUpdatePolicySuccess = () => {
    fetchData();
  };

  const handleBatchEditNoticeGroupSuceess = () => {
    tableRef.value!.clearSelected();
    fetchData();
  };
</script>
<style lang="less" scoped>
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

    :deep(.table-box) {
      .operate-box {
        display: flex;
        gap: 15px;
        // justify-content: flex-end;
        align-items: center;
        padding-right: 15px;

        .operations-more {
          .icon {
            font-size: 18px;
            color: #63656e;
            cursor: pointer;
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
