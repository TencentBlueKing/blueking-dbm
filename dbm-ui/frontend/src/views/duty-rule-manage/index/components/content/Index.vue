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
    <div class="rotation-setting-type-content">
      <div class="create-box">
        <AuthButton
          v-if="activeDbType"
          action-id="duty_rule_create"
          class="w-88 mb-14"
          :resource="activeDbType"
          theme="primary"
          @click="() => handleOperate('create')">
          {{ t('新建') }}
        </AuthButton>
      </div>
      <BkLoading :loading="isTableLoading">
        <DbTable
          ref="tableRef"
          class="table-box"
          :columns="columns"
          :data-source="dataSource"
          :row-class="updateRowClass"
          :show-overflow="false" />
      </BkLoading>
    </div>
    <EditRule
      v-model="isShowEditRuleSideSilder"
      :data="currentRowData"
      :db-type="activeDbType"
      :existed-names="existedNames"
      :page-type="pageType"
      @success="handleSuccess" />
  </ApplyPermissionCatch>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DutyRuleModel from '@services/model/monitor/duty-rule';
  import {
    deleteDutyRule,
    getPriorityDistinct,
    queryDutyRuleList,
    updatePartialDutyRule,
  } from '@services/source/monitor';

  import ApplyPermissionCatch from '@components/apply-permission/Catch.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import EditRule from '../edit-rule/Index.vue';

  import PriorityInput from './components/PriorityInput.vue'
  import RenderRotateTable from './components/RenderRotateTable.vue';

  interface Props {
    activeDbType: string;
  }

  const props = defineProps<Props>();

  const enum RuleStatus {
    TERMINATED = 'TERMINATED', // 已停用
    EXPIRED = 'EXPIRED', // 已失效
    NOT_ACTIVE = 'NOT_ACTIVE', // 未生效
    ACTIVE = 'ACTIVE', // 当前生效
  }

  const { t } = useI18n();

  const dataSource = (params: ServiceParameters<typeof queryDutyRuleList>) => queryDutyRuleList(Object.assign(params, {
    db_type: props.activeDbType
  }), {
    permission: 'catch'
  })

  const tableRef = ref();
  const pageType = ref();
  const isShowEditRuleSideSilder = ref(false);
  const currentRowData = ref<DutyRuleModel>();
  const isTableLoading = ref(false);
  const sortedPriority = ref<number[]>([]);
  const existedNames = ref<string[]>([]);
  const showTipMap = ref<Record<string, boolean>>({});

  const statusMap = {
    [RuleStatus.ACTIVE]: {
      label: t('当前生效'),
      theme: 'success',
      title: t('当前值班人'),
    },
    [RuleStatus.NOT_ACTIVE]: {
      label: t('未生效'),
      theme: 'info',
      title: t('待值班人'),
    },
    [RuleStatus.EXPIRED]: {
      label: t('已失效'),
      theme: '',
      title: t('已值班人'),
    },
    [RuleStatus.TERMINATED]: {
      label: t('已停用'),
      theme: '',
      title: t('待值班人'),
    },
  };

  const columns = computed(() => [
    {
      label: t('规则名称'),
      field: 'name',
      minWidth: 220,
      fixed: 'left',
      render: ({ data }: {data: DutyRuleModel}) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="duty_rule_update"
                permission={data.permission.duty_rule_update}
                resource={props.activeDbType}
                text
                theme="primary"
                onClick={() => handleOperate('edit', data)}>
                {data.name}
              </auth-button>
            ),
            append: () => data.isNewCreated && (
              <MiniTag
                theme='success'
                content="NEW" />
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('状态'),
      field: 'status',
      width: 120,
      render: ({ data }: {data: DutyRuleModel}) => {
        const { label, theme } = statusMap[data.status as RuleStatus];
        return <bk-tag theme={theme}>{label}</bk-tag>;
      },
    },
    {
      label: () => (
        <span
          v-bk-tooltips={{
            content: t('范围 1～100，数字越高代表优先级越高，当有规则冲突时，优先执行数字较高的规则'),
            theme: 'dark',
          }}
          style="border-bottom: 1px dashed #979BA5;">
          {t('优先级')}
        </span>
      ),
      field: 'priority',
      sort: true,
      width: 120,
      render: ({ data }: {data: DutyRuleModel}) => {
        const renderPriority = () => {
          const level = data.priority;
          if (data.is_show_edit){
            return (
              <auth-template
                action-id="duty_rule_update"
                permission={data.permission.duty_rule_update}
                resource={props.activeDbType}>
                <PriorityInput
                  model-value={level}
                  requestHandler={(value: number) => handlePriorityChange(data, value)}/>
              </auth-template>
            )
          }

          let theme = '';
          if (sortedPriority.value.length === 3) {
            const [largest, medium, least] = sortedPriority.value;
            if (level === largest) {
              theme = 'danger';
            } else if (level === medium) {
              theme = 'warning';
            } else if (level === least) {
              theme = 'success';
            }
          }
          return (
            <>
              {
                theme ?
                <bk-tag
                  theme={theme}
                  type="filled">
                  {level}
                </bk-tag> : <bk-tag>{level}</bk-tag>
              }
              <auth-template
                action-id="duty_rule_update"
                permission={data.permission.duty_rule_update}
                resource={props.activeDbType}>
                <db-icon
                  class="edit-icon"
                  type="edit"
                  style="font-size: 18px"
                  onClick={() => handleClickEditPriority(data)} />
              </auth-template>

            </>
          )
        }

        return (
          <div class="priority-box">
            { renderPriority() }
          </div>
        );
      },
    },
    {
      label: t('轮值业务'),
      field: 'status',
      width: 250,
      render: ({ data }: {data: DutyRuleModel}) => {
        if (data.biz_config_display.include) {
          return data.biz_config_display.include.map((biz) => biz.bk_biz_name).join(' , ')
        }
        if (data.biz_config_display.exclude) {
          return `${t('全部业务')} (${t('排除业务')} : ${data.biz_config_display.exclude.map((biz) => biz.bk_biz_name).join(' , ')}) `
        }
        return t('全部业务')
      },
    },
    {
      label: t('轮值表'),
      field: 'duty_arranges',
      width: 280,
      render: ({ data }: {data: DutyRuleModel}) => {
        let title = '';
        if (data.status in statusMap) {
          title = statusMap[data.status as RuleStatus].title;
        } else {
          return <div class="display-text" style="width: 27px;">--</div>;
        }
        const peopleSet = data.duty_arranges.reduce((result, item) => {
          item.members.forEach((member) => {
            result.add(member);
          });
          return result;
        }, new Set<string>());
        const peoples = [...peopleSet].join(' , ');
        return (
          <div class="rotate-table-column">
            <bk-popover
              placement="bottom"
              theme="light"
              width={780}
              popoverDelay={[500, 50]}>
              {{
                default: () => (
                  <div class="display-text">{title}: {peoples}</div>
                ),
                content: () => <RenderRotateTable data={data} />,
              }}
            </bk-popover>
          </div>
        );
      },
    },
    {
      label: t('生效时间'),
      field: 'effective_time',
      width: 240,
      render: ({ data }: { data: DutyRuleModel }) => <span>{data.effectiveTimeDisplay}</span>,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      sort: true,
      width: 240,
      render: ({ data }: { data: DutyRuleModel }) => <span>{data.updateAtDisplay}</span>,
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 120,
    },
    {
      label: t('启停'),
      field: 'is_enabled',
      width: 80,
      showOverflow: false,
      render: ({ data }: { data: DutyRuleModel }) => (
        <bk-pop-confirm
          title={t('确认停用该策略？')}
          content={t('停用后，所有的业务将会停用该策略，请谨慎操作！')}
          width="320"
          is-show={showTipMap.value[data.id]}
          trigger="manual"
          placement="bottom"
          onConfirm={() => handleClickConfirm(data)}
          onCancel={() => handleCancelConfirm(data)}
        >
          <auth-switcher
            action-id="duty_rule_update"
            permission={data.permission.duty_rule_update}
            resource={props.activeDbType}
            size="small"
            v-model={data.is_enabled}
            theme="primary"
            before-change={(isEnable: boolean) => enableRequestHandler(isEnable, data)}
          />
        </bk-pop-confirm>
      ),
    },
    {
      label: t('操作'),
      fixed: 'right',
      showOverflow: false,
      field: '',
      width: 140,
      render: ({ data }: {data: DutyRuleModel}) => (
      <div class="operate-box">
        <auth-button
          action-id="duty_rule_update"
          permission={data.permission.duty_rule_update}
          resource={props.activeDbType}
          text
          theme="primary"
          onClick={() => handleOperate('edit', data)}>
          {t('编辑')}
        </auth-button>
        <auth-button
          action-id="duty_rule_create"
          permission={data.permission.duty_rule_create}
          resource={props.activeDbType}
          text
          theme="primary"
          onClick={() => handleOperate('clone', data)}>
          {t('克隆')}
        </auth-button>
        {!data.is_enabled && (
          <auth-button
            action-id="duty_rule_destroy"
            permission={data.permission.duty_rule_destroy}
            resource={props.activeDbType}
            text
            theme="primary"
            onClick={() => handleDelete(data)}>
            {t('删除')}
          </auth-button>
        )}
      </div>),
    },
  ]);


  const { run: runGetPriorityDistinct } = useRequest(getPriorityDistinct, {
    onSuccess: (list) => {
      if (list.length > 3) {
        sortedPriority.value = list.slice(0, 3);
        return;
      }
      sortedPriority.value = list;
    },
  });

  let enableRequestHandlerResolver = null as null | ((value: boolean) => void);
  let enableRequestHandlerRejecter = null as null | (() => void);

  watch(() => props.activeDbType, (type) => {
    if (type) {
      setTimeout(() => {
        fetchHostNodes();
      });
    }
  }, {
    immediate: true,
  });

  const updateRowClass = (row: DutyRuleModel) => (row.isNewCreated ? 'is-new' : '');

  const fetchHostNodes = async () => {
    isTableLoading.value = true;
    try {
      await tableRef.value.fetchData({}, {
        db_type: props.activeDbType,
      });
    } finally {
      isTableLoading.value = false;
    }
  };

  const handleClickEditPriority = (data: DutyRuleModel) => {
    Object.assign(data, {
      is_show_edit: true,
    });
  };

  const handlePriorityChange = async (row: DutyRuleModel, value: number) => {
    let priority = value;
    if (priority < 1) {
      priority = 1;
    } else if (priority > 100) {
      priority = 100;
    }
    try {
      const updateResult = await updatePartialDutyRule(row.id, {
        priority,
      })

      if (updateResult.priority === priority) {
        // 设置成功
        messageSuccess(t('优先级设置成功'));
      }
      runGetPriorityDistinct();
      window.changeConfirm = false;
    } finally {
      Object.assign(row, {
        priority,
        is_show_edit: false,
      })
    }
  };

  const enableRequestHandler = (isEnable: boolean, row: DutyRuleModel) =>
    new Promise((resolve, reject) => {
      enableRequestHandlerResolver = resolve;
      enableRequestHandlerRejecter = reject;
      if (isEnable) {
        updatePartialDutyRule(row.id, {
          is_enabled: true,
        }).then(() => {
          resolve(true);
          messageSuccess(t('启用成功'));
        }).catch(() => {
          reject();
        })
      } else {
        showTipMap.value[row.id] = true;
      }
    });

  const handleClickConfirm = async (row: DutyRuleModel) => {
    try {
      await updatePartialDutyRule(row.id, {
        is_enabled: false,
      });
      // 停用成功
      enableRequestHandlerResolver!(true);
      showTipMap.value[row.id] = false;
      messageSuccess(t('停用成功'));
    } finally {
      enableRequestHandlerRejecter!();
    }
  };

  const handleCancelConfirm = (row: DutyRuleModel) => {
    showTipMap.value[row.id] = false;
    enableRequestHandlerRejecter!();
  };

  const handleOperate = (type: string, row?: DutyRuleModel) => {
    existedNames.value = tableRef.value.getData().map((item: { name: string; }) => item.name);
    currentRowData.value = row;
    pageType.value = type;
    isShowEditRuleSideSilder.value = true;
  };

  const handleDelete = async (row: DutyRuleModel) => {
    InfoBox({
      title: t('确认删除该轮值?'),
      subTitle: t('重置 Secure Key,需自定修改 Template 中的地址字段！'),
      width: 450,
      onConfirm: async () => {
        await deleteDutyRule({ id: row.id });
        fetchHostNodes();
      } });
  };

  const handleSuccess = () => {
    fetchHostNodes();
    window.changeConfirm = false;
  };
</script>
<style lang="less" scoped>
  .rotation-setting-type-content {
    display: flex;
    flex-direction: column;

    .create-box {
      width: 100%;
    }

    :deep(.table-box) {
      .priority-box {
        display: flex;
        align-items: center;

        &:hover {
          .edit-icon {
            display: block;
          }
        }

        .edit-icon {
          display: none;
          color: #3a84ff;
          cursor: pointer;
        }
      }

      .rotate-table-column {
        width: 100%;
        overflow: hidden;
      }

      .display-text {
        display: inline-block;
        height: 22px;
        padding: 0 8px;
        overflow: hidden;
        line-height: 22px;
        color: #63656e;
        text-overflow: ellipsis;
        white-space: nowrap;
        cursor: pointer;
        background: #f0f1f5;
        border-radius: 2px;
      }

      .operate-box {
        display: flex;
        gap: 15px;
        align-items: center;

        span {
          color: #3a84ff;
          cursor: pointer;
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
