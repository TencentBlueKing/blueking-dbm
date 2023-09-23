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
  <div class="type-content-box">
    <BkSearchSelect
      v-model="searchValue"
      class="input-box"
      :data="searchSelectList"
      :placeholder="t('请输入策略关键字或选择条件搜索')"
      unique-select
      value-split-code="+"
      @search="fetchHostNodes" />
    <DbOriginalTable
      class="table-box"
      :columns="columns"
      :data="tableData"
      :pagination="pagination"
      remote-pagination
      @page-limit-change="handeChangeLimit"
      @page-value-change="handleChangePage"
      @refresh="fetchHostNodes" />
  </div>
  <EditRule
    v-model="isShowEditStrrategySideSilder"
    :alarm-group-list="alarmGroupList"
    :alarm-group-name-map="alarmGroupNameMap"
    :bizs-map="bizsMap"
    :data="currentChoosedRow"
    :db-type="activeDbType"
    :page-status="sliderPageType"
    @success="handleUpdatePolicySuccess" />
</template>
<script lang="tsx">
  import {
    deletePolicy,
    disablePolicy,
    enablePolicy,
    getAlarmGroupList,
    queryMonitorPolicyList  } from '@services/monitor';

  export type RowData = ServiceReturnType<typeof queryMonitorPolicyList>['results'][0];
</script>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { useGlobalBizs } from '@stores';

  import MiniTag from '@components/mini-tag/index.vue';

  import EditRule from '../edit-strategy/Index.vue';

  import RenderTargetItem from './RenderTargetItem.vue';

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

  useRequest(getAlarmGroupList, {
    defaultParams: [{
      bk_biz_id: currentBizId,
      dbtype: props.activeDbType,
    }],
    onSuccess: (res) => {
      alarmGroupList.value = res.results.map((item) => {
        alarmGroupNameMap[item.id] = item.name;
        return ({
          label: item.name,
          value: item.id,
        });
      });
    },
    onError: (e) => {
      console.error('alarm list error:', e);
    },
  });

  const isShowEditStrrategySideSilder = ref(false);
  const currentChoosedRow = ref({} as RowData);
  const searchValue = ref<Array<SearchSelectItem & {values: SearchSelectItem[]}>>([]);
  const alarmGroupList = ref<SelectItem[]>([]);
  const tableData = ref<RowData[]>([]);
  const sliderPageType = ref('edit');
  const pagination = ref({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });

  const bizsMap = computed(() => bizs.reduce((results, item) => {
    // eslint-disable-next-line no-param-reassign
    results[item.bk_biz_id] = item.name;
    return results;
  }, {} as Record<string, string>));

  const isSelectedAll = computed(() => {
    const checkedLen = tableData.value.filter(item => item.is_checked).length;
    const totalLen = tableData.value.length;
    return totalLen > 0 &&  checkedLen === totalLen;
  });

  const isIndeterminate = computed(() => {
    const checkedLen = tableData.value.filter(item => item.is_checked).length;
    const totalLen = tableData.value.length;
    return totalLen > 0 && checkedLen > 0 && checkedLen !== totalLen;
  });

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
        id: item.value,
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
    const commonParams = {
      bk_biz_id: currentBizId,
      db_type: props.activeDbType,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    };
    return {
      ...searchParams,
      ...commonParams,
    };
  });

  const alarmGroupNameMap: Record<string, string> = {};
  const columns = [
    {
      label: () => (
        <div class="strategy-title">
          <bk-checkbox
          indeterminate={isIndeterminate.value}
          model-value={isSelectedAll.value}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={handleSelectPageAll}
        />
          <span class="name">{t('策略名称')}</span>
        </div>
      ),
      field: 'name',
      minWidth: 150,
      render: ({ row }: {row: RowData}) => {
        // const { status } = data;
        const isInner = row.bk_biz_id === 0;
        const isStopped = false;
        const isDanger = false;
        // const isInvalid = status === 3;
        return (
          <div class="strategy-title">
            <bk-checkbox
              model-value={row.is_checked}
              onClick={(e: Event) => e.stopPropagation()}
              onChange={(value: boolean) => handleTableSelectOne(value, row)}
            />
            <span class="name" style={{ color: isStopped ? '#979BA5' : '#3A84FF' }}>{row.name}</span>
            {isInner && <MiniTag content={t('内置')} />}
            {isStopped && <MiniTag content={t('已停用')} />}
            {isDanger && (
              <div class="danger-box" v-bk-tooltips={{
                content: '当前有 2 个未恢复事件',
              }}>
                <i class="db-icon-alert icon-dander" />
                <span class="text">3</span>
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
          Array.isArray(row.targets)
            && row.targets.map((item) => {
              const title = item.rule.key;
              let list = item.rule.value;
              if (title === 'app_id') {
                // 业务级
                list = [bizsMap.value[list[0]]];
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
            Array.isArray(row.notify_groups) && row.notify_groups.map(item => (
              <span class="notify-box">
                <db-icon type="yonghuzu" style="font-size: 16px" />
                <span class="dba">{alarmGroupNameMap[item]}</span>
              </span>
            ))
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
        <bk-switcher v-model={row.is_enabled} theme="primary" onChange={() => handleChangeSwitch(row)}/>
      </bk-pop-confirm>
      ),
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      showOverflowTooltip: true,
      sort: true,
      width: 120,
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
          <span>{t('监控告警')}</span>
          <bk-dropdown class="operations-more">
            {{
              default: () => <i class="db-icon-more" style="color:#63656E;font-size:18px"></i>,
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

  watch(reqParams, () => {
    fetchHostNodes();
  }, {
    deep: true,
  });

  watch(() => props.activeDbType, (type) => {
    if (type) {
      setTimeout(() => {
        fetchHostNodes();
      });
    }
  }, {
    immediate: true,
  });

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    fetchHostNodes();
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    pagination.value.current = 1;
    fetchHostNodes();
  };

  const fetchHostNodes = async () => {
    const ret = await queryMonitorPolicyList(reqParams.value);
    tableData.value = ret.results;
    pagination.value.count = ret.count;
  };

  const handleSelectPageAll = (checked: boolean) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        isChecked: checked,
      });
    });
  };

  const handleTableSelectOne = (checked: boolean, data: RowData) => {
    Object.assign(data, {
      isChecked: checked,
    });
  };

  const handleClickDelete = (data: RowData) => {
    InfoBox({
      infoType: 'warning',
      title: t('确认删除该策略？'),
      subTitle: t('将会删除所有内容，请谨慎操作！'),
      width: 400,
      onConfirm: async () => {
        const r = await deletePolicy(data.id);
        console.log('delete policy: ', r);
        setTimeout(() => {
          fetchHostNodes();
        }, 500);
      } });
  };

  const handleChangeSwitch = async (row: RowData) => {
    if (!row.is_enabled) {
      nextTick(() => {
        Object.assign(row, {
          is_show_tip: true,
          is_enabled: !row.is_enabled,
        });
      });
    } else {
      // 启用
      const r = await enablePolicy(row.id);
      Object.assign(row, {
        is_enabled: r,
      });
    }
  };

  const handleClickConfirm = async (row: RowData) => {
    const r = await disablePolicy(row.id);
    if (!r) {
      // 停用成功
      Object.assign(row, {
        is_enabled: false,
      });
    }
    Object.assign(row, {
      is_show_tip: false,
    });
  };

  const handleCancelConfirm = (row: RowData) => {
    Object.assign(row, {
      is_show_tip: false,
    });
  };

  const handleOpenSlider = (row: RowData, type: string) => {
    console.log('data>>', row);
    sliderPageType.value = type;
    currentChoosedRow.value = row;
    isShowEditStrrategySideSilder.value = true;
  };

  const handleUpdatePolicySuccess = () => {
    fetchHostNodes();
  };

</script>
<style lang="less" scoped>
.type-content-box {
  display: flex;
  flex-direction: column;

  .input-box {
    width: 600px;
    height: 32px;
    margin-bottom: 16px;
  }

  .table-box {
    :deep(.strategy-title) {
      display: flex;
      align-items: center;

      .name {
        margin-left: 8px;
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

    :deep(.targets-box) {
      display: flex;
      width: 100%;
      flex-flow: column wrap;
      padding: 5px 15px;
    }

    :deep(.alarm-group) {
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

    :deep(.operate-box) {
      display: flex;
      gap: 15px;
      align-items: center;

      span {
        color: #3A84FF;
        cursor: pointer;
      }
    }
  }

}

</style>
