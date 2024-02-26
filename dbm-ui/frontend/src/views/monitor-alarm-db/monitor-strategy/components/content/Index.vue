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
  <div class="monitor-strategy-type-content">
    <BkSearchSelect
      v-model="searchValue"
      class="input-box"
      :data="searchSelectList"
      :placeholder="t('请选择条件搜索')"
      unique-select
      value-split-code="+"
      @search="fetchHostNodes" />
    <DbTable
      ref="tableRef"
      class="table-box"
      :columns="columns"
      :data-source="queryMonitorPolicyList"
      releate-url-query
      :row-class="updateRowClass"
      @clear-search="handleClearSearch" />
  </div>
  <EditStrategy
    v-model="isShowEditStrrategySideSilder"
    :alarm-group-list="alarmGroupList"
    :alarm-group-name-map="alarmGroupNameMap"
    :bizs-map="bizsMap"
    :cluster-list="clusterList"
    :data="currentChoosedRow"
    :db-type="activeDbType"
    :default-notify-id="defaultNotifyId"
    :existed-names="existedNames"
    :module-list="moduleList"
    :page-status="sliderPageType"
    @cancel="handleUpdatePolicyCancel"
    @success="handleUpdatePolicySuccess" />
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import {
    deletePolicy,
    disablePolicy,
    enablePolicy,
    getAlarmGroupList,
    getClusterList,
    getDbModuleList,
    queryMonitorPolicyList,
  } from '@services/monitor';

  import { useGlobalBizs } from '@stores';

  import MiniTag from '@components/mini-tag/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import EditStrategy from '../edit-strategy/Index.vue';

  import RenderNotifyGroup from './RenderNotifyGroup.vue';
  import RenderTargetItem from './RenderTargetItem.vue';

  export type RowData = ServiceReturnType<typeof queryMonitorPolicyList>['results'][0];

  interface Props {
    activeDbType: string;
  }

  interface SearchSelectItem {
    id: string,
    name: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId, bizs } = useGlobalBizs();
  const { notifyGroupId } = useRoute().query as { notifyGroupId: string };

  const tableRef = ref();
  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as MonitorPolicyModel);
  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const alarmGroupList = ref<SelectItem<number>[]>([]);
  const sliderPageType = ref('edit');
  const moduleList = ref<SelectItem<string>[]>([]);
  const clusterList = ref<SelectItem<string>[]>([]);
  const isTableLoading = ref(false);
  const existedNames = ref<string[]>([]);
  const showTipMap = ref<Record<string, boolean>>({});
  const defaultNotifyId = ref(0);

  async function fetchHostNodes() {
    isTableLoading.value = true;
    try {
      await tableRef.value.fetchData({ ...reqParams.value }, {
        bk_biz_id: currentBizId,
        db_type: props.activeDbType,
      });
    } finally {
      isTableLoading.value = false;
    }
  }

  const bizsMap = computed(() => bizs.reduce((results, item) => {
    // eslint-disable-next-line no-param-reassign
    results[item.bk_biz_id] = item.name;
    return results;
  }, {} as Record<string, string>));

  const searchSelectList = computed(() => ([
    {
      name: t('策略名称'),
      id: 'name',
    },
    {
      name: t('监控目标'),
      id: 'target_keyword',
    },
    {
      name: t('告警组'),
      id: 'notify_groups',
      multiple: true,
      children: alarmGroupList.value.map(item => ({
        id: String(item.value),
        name: item.label,
      })) as SearchSelectItem[],
    },
    {
      name: t('更新人'),
      id: 'updater',
    },
  ]));

  const reqParams = computed(() => {
    const searchParams = searchValue.value.reduce((obj, item) => {
      Object.assign(obj, {
        [item.id]: item.values.map(data => data.id).join(','),
      });
      return obj;
    }, {} as Record<string, string>);
    return {
      ...searchParams,
    };
  });

  const alarmGroupNameMap: Record<string, string> = {};
  const dbModuleMap: Record<string, string> = {};
  const columns = [
    {
      label: t('策略名称'),
      field: 'name',
      fixed: 'left',
      minWidth: 150,
      width: 280,
      showOverflowTooltip: false,
      render: ({ data }: {data: MonitorPolicyModel}) => {
        const isInner = data.bk_biz_id === 0;
        const isDanger = data.event_count > 0;
        const pageType = isInner ? 'read' : 'edit';
        return (
          <TextOverflowLayout>
            {{
              default: () => (
                <bk-button
                  text
                  theme="primary"
                  disabled={!data.is_enabled}
                  onClick={() => handleOpenSlider(data, pageType)}>
                  {data.name}
                </bk-button>
              ),
              append: () => (
                <>
                  {isInner && <MiniTag content={t('内置')} />}
                  {!data.is_enabled && <MiniTag content={t('已停用')} />}
                  {isDanger && (
                    <div class="monitor-alarm-danger-box" v-bk-tooltips={{
                      content: t('当前有n个未恢复事件', { n: data.event_count }),
                    }}>
                    <MiniTag
                      theme='danger'
                      iconType='alert'
                      content={data.event_count}
                      onTag-click={() => handleGoMonitorPage(data.event_url)}/>
                    </div>
                  )}
                  {data.isNewCreated && <MiniTag theme='success' content="NEW" />}
                </>
              ),
            }}
          </TextOverflowLayout>
        );
      },
    },
    {
      label: t('监控目标'),
      field: 'targets',
      minWidth: 180,
      render: ({ data }: {data: MonitorPolicyModel}) => (
        <div class="targets-box">
          {
            data.targets.map((item) => {
              const title = item.rule.key;
              let list = item.rule.value;
              if (title === 'appid') {
                // 业务级
                list = [bizsMap.value[list[0]]];
              }
              if (title === 'db_module') {
                // 模块
                list = item.rule.value.map(item => dbModuleMap[item]);
              }
              return <RenderTargetItem title={title} list={list}/>;
            })
          }
        </div>
      ),
    },
    {
      label: t('告警组'),
      field: 'notify_groups',
      minWidth: 180,
      render: ({ data }: {data: MonitorPolicyModel}) => {
        if (data.notify_groups.length === 0) {
          return '--';
        }

        const dataList: {
          id: string,
          displayName: string,
        }[] = [];
        data.notify_groups.forEach((id) => {
          if (id in alarmGroupNameMap) {
            dataList.push({
              id: `${id}`,
              displayName: alarmGroupNameMap[id],
            });
          }
        });
        return <RenderNotifyGroup data={dataList} />;
      },
    },
    {
      label: t('启停'),
      field: 'is_enabled',
      showOverflowTooltip: true,
      minWidth: 60,
      render: ({ data }: {data: MonitorPolicyModel}) => {
        const isInner = data.bk_biz_id === 0;
        return (
          <bk-pop-confirm
            title={t('确认停用该策略？')}
            content={t('停用后所有监控动作将会停止，请谨慎操作！')}
            disabled={isInner}
            width="320"
            is-show={showTipMap.value[data.id]}
            trigger="manual"
            placement="bottom"
            onConfirm={() => handleClickConfirm(data)}
            onCancel={() => handleCancelConfirm(data)}
          >
            <bk-switcher
              size="small"
              disabled={isInner}
              v-model={data.is_enabled}
              theme="primary"
              onChange={() => handleChangeSwitch(data)}
            />
          </bk-pop-confirm>
        );
      },
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      minWidth: 160,
      render: ({ data }: {data: RowData}) => <span>{data.updateAtDisplay}</span>,
    },
    {
      label: t('更新人'),
      field: 'updater',
      showOverflowTooltip: true,
      minWidth: 100,
      render: ({ data }: {data: RowData}) => <span>{data.updater || '--'}</span>,
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ data }: {data: MonitorPolicyModel}) => {
        const isInner = data.bk_biz_id === 0;
        return (
          <div class="operate-box">
          {!isInner && (
            <auth-button
              text
              action-id="monitor_policy_edit"
              permission={data.permission.monitor_policy_edit}
              theme="primary"
              onClick={() => handleOpenSlider(data, 'edit')}>
              {t('编辑')}
            </auth-button>
          )}
          <bk-button
            text
            theme="primary"
            onClick={() => handleOpenSlider(data, 'clone')}>
            {t('克隆')}
          </bk-button>
          <bk-button
            text
            theme="primary"
            onClick={() => handleOpenMonitorAlarmPage(data.event_url)}>
            {t('监控告警')}
          </bk-button>
          <bk-dropdown
            class="operations-more"
            popover-options={{ popoverDelay: 0, trigger: 'click' }}>
            {{
              default: () => <db-icon type="more" class="icon"/>,
              content: () => (
                <bk-dropdown-menu class="operations-menu">
                  <bk-dropdown-item>
                    <auth-button
                      disabled={isInner}
                      text
                      action-id="monitor_policy_delete"
                      permission={data.permission.monitor_policy_delete}
                      onClick={() => handleClickDelete(data)}>
                        {t('删除')}
                      </auth-button>
                    </bk-dropdown-item>
                </bk-dropdown-menu>
              ),
            }}
          </bk-dropdown>
        </div>
        );
      },
    },
  ];

  const { run: fetchAlarmGroupList } = useRequest(getAlarmGroupList, {
    manual: true,
    onSuccess: (res) => {
      const groupList: SelectItem<number>[] = [];
      res.results.forEach((item) => {
        groupList.push({
          label: item.name,
          value: item.id,
        });
        alarmGroupNameMap[item.id] = item.name;
        if (item.db_type === props.activeDbType) {
          defaultNotifyId.value = item.id;
        }
      });
      alarmGroupList.value = groupList;
      if (notifyGroupId !== undefined) {
        searchValue.value = [{
          id: 'notify_groups',
          name: t('告警组'),
          values: [
            {
              id: notifyGroupId,
              name: alarmGroupNameMap[notifyGroupId],
            }],
        }];
      }
    },
  });

  const { run: fetchClusers } = useRequest(getClusterList, {
    manual: true,
    onSuccess: (res) => {
      clusterList.value = res.map(item => ({
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
        return ({
          label: item.db_module_name,
          value: String(item.db_module_id),
        });
      });
    },
  });

  const { run: runEnablePolicy } = useRequest(enablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (isEnabled) {
        messageSuccess(t('启用成功'));
        fetchHostNodes();
      }
    },
  });

  const { run: runDisablePolicy } = useRequest(disablePolicy, {
    manual: true,
    onSuccess: (isEnabled) => {
      if (!isEnabled) {
        // 停用成功
        messageSuccess(t('停用成功'));
        fetchHostNodes();
      }
    },
  });

  const { run: runDeletePolicy } = useRequest(deletePolicy, {
    manual: true,
    onSuccess: (isDeleted) => {
      if (isDeleted === null) {
        // 停用成功
        messageSuccess(t('删除成功'));
        fetchHostNodes();
      }
    },
  });

  watch(reqParams, () => {
    setTimeout(() => {
      fetchHostNodes();
    });
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => props.activeDbType, (type) => {
    if (type) {
      setTimeout(() => {
        fetchHostNodes();
        fetchClusers({
          dbtype: type,
          bk_biz_id: currentBizId,
        });
        fetchAlarmGroupList({
          bk_biz_id: currentBizId,
          offset: 0,
          limit: -1,
          db_type: type,
        });
        fetchDbModuleList({
          dbtype: type,
        });
      });
    }
  }, {
    immediate: true,
  });

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
      title: t('确认删除该策略？'),
      subTitle: t('将会删除所有内容，请谨慎操作！'),
      width: 400,
      onConfirm: () => {
        runDeletePolicy({ id: data.id });
      } });
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
    existedNames.value = tableRef.value.getData().map((item: { name: string; }) => item.name);
    sliderPageType.value = type;
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

  const handleOpenMonitorAlarmPage = (url: string) => {
    window.open(url, '_blank');
  };

  const handleUpdatePolicySuccess = () => {
    fetchHostNodes();
    window.changeConfirm = false;
  };

  const handleUpdatePolicyCancel = () => {
    currentChoosedRow.value = {} as MonitorPolicyModel;
    window.changeConfirm = false;
  };

</script>
<style lang="less" scoped>
.monitor-strategy-type-content {
  display: flex;
  flex-direction: column;

  .input-box {
    width: 600px;
    height: 32px;
    margin-bottom: 16px;
  }

  :deep(.table-box) {
    .targets-box {
      display: flex;
      width: 100%;
      flex-flow: column wrap;
      padding: 5px 15px;
    }

    .operate-box {
      display: flex;
      gap: 15px;
      justify-content: flex-end;
      align-items: center;

      .operations-more {
        .icon {
          font-size:18px;
          color:#63656E;
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
<style lang="less">
.monitor-alarm-danger-box {
  .bk-tag {
    cursor: pointer;
  }
}
</style>
