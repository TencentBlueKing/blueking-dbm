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
      :placeholder="t('请输入策略关键字或选择条件搜索')"
      unique-select
      value-split-code="+"
      @search="fetchHostNodes" />
    <BkLoading :loading="isTableLoading">
      <DbTable
        ref="tableRef"
        class="table-box"
        :columns="columns"
        :data-source="queryMonitorPolicyList" />
    </BkLoading>
  </div>
  <EditRule
    v-model="isShowEditStrrategySideSilder"
    :alarm-group-list="alarmGroupList"
    :alarm-group-name-map="alarmGroupNameMap"
    :bizs-map="bizsMap"
    :cluster-list="clusterList"
    :data="currentChoosedRow"
    :db-type="activeDbType"
    :module-list="moduleList"
    :page-status="sliderPageType"
    @success="handleUpdatePolicySuccess" />
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

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

  import { messageSuccess } from '@utils';

  import EditRule from '../edit-strategy/Index.vue';

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
  const { notifyGroupId } = useRoute().params as { notifyGroupId: string };

  const tableRef = ref();
  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as RowData);
  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const alarmGroupList = ref<SelectItem<string>[]>([]);
  const sliderPageType = ref('edit');
  const moduleList = ref<SelectItem<string>[]>([]);
  const clusterList = ref<SelectItem<string>[]>([]);
  const isTableLoading = ref(false);

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
      minWidth: 150,
      render: ({ row }: {row: RowData}) => {
        const isInner = row.bk_biz_id === 0;
        const isDanger = row.event_count > 0;
        const pageType = isInner ? 'read' : 'edit';
        // const isInvalid = status === 3;
        return (
          <div class="strategy-title">
            <span class="name" style={{ color: !row.is_enabled ? '#979BA5' : '#3A84FF' }} onClick={() => handleOpenSlider(row, pageType)}>{row.name}</span>
            {isInner && <MiniTag content={t('内置')} />}
            {!row.is_enabled && <MiniTag content={t('已停用')} />}
             {isDanger && (
              <div class="danger-box" v-bk-tooltips={{
                content: t('当前有n个未恢复事件', { n: row.event_count }),
              }}>
                <db-icon type="alert" class="icon-dander" />
                <span class="text">{row.event_count}</span>
              </div>
            )}
            {/* {
              isInvalid && <i v-bk-tooltips={{
                content: '监控目标失效',
              }} class="db-icon-warn-lightning icon-warn" />
            } */}
          </div>
        );
      },
    },
    {
      label: t('监控目标'),
      field: 'targets',
      minWidth: 180,
      render: ({ row }: {row: RowData}) => (
        <div class="targets-box">
          {
            row.targets.map((item) => {
              const title = item.rule.key;
              let list = item.rule.value;
              if (title === 'app_id') {
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
      minWidth: 280,
      render: ({ row }: {row: RowData}) => (
        <div class="alarm-group">
          {
            row.notify_groups.map((item) => {
              if (alarmGroupNameMap[item]) {
                return (
                  <span class="notify-box">
                    <db-icon type="yonghuzu" style="font-size: 16px" />
                    <span class="dba">{alarmGroupNameMap[item]}</span>
                  </span>
                );
              }
              return null;
            })
          }
        </div>
      ),
    },
    {
      label: t('启停'),
      field: 'is_enabled',
      showOverflowTooltip: true,
      width: 120,
      render: ({ row }: {row: RowData}) => (
        <bk-pop-confirm
          title={t('确认停用该策略？')}
          content={t('停用后所有监控动作将会停止，请谨慎操作！')}
          width="320"
          is-show={row.is_show_tip}
          trigger="manual"
          placement="bottom"
          onConfirm={() => handleClickConfirm(row)}
          onCancel={() => handleCancelConfirm(row)}
        >
        <bk-switcher size="small" v-model={row.is_enabled} theme="primary" onChange={() => handleChangeSwitch(row)}/>
      </bk-pop-confirm>
      ),
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      width: 180,
    },
    {
      label: t('更新人'),
      field: 'updater',
      showOverflowTooltip: true,
      width: 120,
    },
    {
      label: t('操作'),
      fixed: 'right',
      field: '',
      width: 180,
      render: ({ row }: {row: RowData}) => {
        const isShowEdit = row.bk_biz_id !== 0;
        return (
          <div class="operate-box">
          {isShowEdit && <span onClick={() => handleOpenSlider(row, 'edit')}>{t('编辑')}</span>}
          <span onClick={() => handleOpenSlider(row, 'clone')}>{t('克隆')}</span>
          <span onClick={() => handleOpenMonitorAlarmPage(row.event_url)}>{t('监控告警')}</span>
          <bk-dropdown class="operations-more" popover-options={{ popoverDelay: 0, trigger: 'click' }}>
            {{
              default: () => <db-icon type="more" class="icon"/>,
              content: () => (
                <bk-dropdown-menu class="operations-menu">
                  <bk-dropdown-item onClick={() => handleClickDelete(row)}>{t('删除')}</bk-dropdown-item>
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
      alarmGroupList.value = res.results.map((item) => {
        alarmGroupNameMap[item.id] = item.name;
        return ({
          label: item.name,
          value: String(item.id),
        });
      });
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
        });
        fetchAlarmGroupList({
          bk_biz_id: currentBizId,
          dbtype: type,
        });
        fetchDbModuleList({
          dbtype: type,
        });
      });
    }
  }, {
    immediate: true,
  });

  const handleClickDelete = (data: RowData) => {
    InfoBox({
      infoType: 'warning',
      title: t('确认删除该策略？'),
      subTitle: t('将会删除所有内容，请谨慎操作！'),
      width: 400,
      onConfirm: () => {
        runDeletePolicy(data.id);
      } });
  };

  const handleChangeSwitch = (row: RowData) => {
    if (!row.is_enabled) {
      nextTick(() => {
        Object.assign(row, {
          is_show_tip: true,
          is_enabled: !row.is_enabled,
        });
      });
    } else {
      // 启用
      runEnablePolicy(row.id);
    }
  };

  const handleClickConfirm = (row: RowData) => {
    runDisablePolicy(row.id);
  };

  const handleCancelConfirm = (row: RowData) => {
    Object.assign(row, {
      is_show_tip: false,
    });
  };

  const handleOpenSlider = (row: RowData, type: string) => {
    sliderPageType.value = type;
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

  const handleOpenMonitorAlarmPage = (url: string) => {
    window.open(url, '_blank');
  };

  const handleUpdatePolicySuccess = () => {
    fetchHostNodes();
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
    .strategy-title {
      display: flex;
      align-items: center;

      .name {
        margin-left: 8px;
        cursor: pointer;
      }

      .bk-tag {
        margin-right: -2px !important;
      }

      .danger-box {
        display: flex;
        height: 16px;
        padding: 0 7px;
        margin-left: 10px;
        cursor: pointer;
        background: #FDD;
        border-radius: 8px;
        align-items: center;


        .icon-dander {
          color: #EA3636;
        }

        .text {
          margin-left: 2px;
          color: #EA3636;
        }

      }

      .icon-warn {
        margin-left: 8px;
        color: #FF9C01;
        cursor: pointer;
      }
    }

    .targets-box {
      display: flex;
      width: 100%;
      flex-flow: column wrap;
      padding: 5px 15px;
    }

    .alarm-group {
      display: flex;
      width: 100%;
      padding: 5px 15px;
      overflow: hidden;
      text-overflow: ellipsis;
      flex-wrap: wrap;
      gap: 5px;

      .notify-box{
        display: flex;
        height: 22px;
        padding: 2.5px 5px;
        background: #F0F1F5;
        border-radius: 2px;
        box-sizing: border-box;
        align-items: center;

        .dba {
          margin-left: 8px;
        }
      }

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


      span {
        color: #3A84FF;
        cursor: pointer;
      }
    }
  }

}

</style>
