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
          action-id="duty_rule_manage"
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
          :data-source="dataSource"
          :row-class-name="updateRowClass"
          row-key="id">
          <TableColumn
            col-key="name"
            fixed="left"
            :min-width="220"
            :title="t('规则名称')">
            <template #default="{ row }: { row: DutyRuleModel }">
              <TextOverflowLayout>
                <AuthButton
                  action-id="duty_rule_manage"
                  :permission="row.permission.duty_rule_manage"
                  :resource="activeDbType"
                  text
                  theme="primary"
                  @click="() => handleOperate('edit', row)">
                  {{ row.name }}
                </AuthButton>
                <template #append>
                  <MiniTag
                    v-if="row.isNewCreated"
                    content="NEW"
                    theme="success" />
                </template>
              </TextOverflowLayout>
            </template>
          </TableColumn>
          <TableColumn
            col-key="status"
            :title="t('状态')"
            :width="120">
            <template #default="{ row }: { row: DutyRuleModel }">
              <BkTag :theme="getStatusInfo(row).theme">
                {{ getStatusInfo(row).label }}
              </BkTag>
            </template>
          </TableColumn>
          <TableColumn
            col-key="priority"
            :width="120">
            <template #title>
              <span
                v-bk-tooltips="{
                  content: t('范围 1～100，数字越高代表优先级越高，当有规则冲突时，优先执行数字较高的规则'),
                  theme: 'dark',
                }"
                style="border-bottom: 1px dashed #979ba5">
                {{ t('优先级') }}
              </span>
            </template>
            <template #default="{ row }: { row: DutyRuleModel }">
              <div class="priority-box">
                <AuthTemplate
                  v-if="row.is_show_edit"
                  action-id="duty_rule_manage"
                  :permission="row.permission.duty_rule_manage"
                  :resource="activeDbType">
                  <PriorityInput
                    :model-value="row.priority"
                    :request-handler="(value: number) => handlePriorityChange(row, value)" />
                </AuthTemplate>
                <template v-else>
                  <BkTag
                    v-if="getPriorityTheme(row)"
                    :theme="getPriorityTheme(row)"
                    type="filled">
                    {{ row.priority }}
                  </BkTag>
                  <BkTag v-else>
                    {{ row.priority }}
                  </BkTag>
                  <AuthTemplate
                    action-id="duty_rule_manage"
                    :permission="row.permission.duty_rule_manage"
                    :resource="activeDbType">
                    <DbIcon
                      class="edit-icon"
                      style="font-size: 18px"
                      type="edit"
                      @click="() => handleClickEditPriority(row)" />
                  </AuthTemplate>
                </template>
              </div>
            </template>
          </TableColumn>
          <TableColumn
            col-key="biz_config_display"
            :title="t('轮值业务')"
            :width="250">
            <template #default="{ row }: { row: DutyRuleModel }">
              {{ getBizConfigDisplay(row) }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="duty_arranges"
            :title="t('轮值表')"
            :width="280">
            <template #default="{ row }: { row: DutyRuleModel }">
              <div
                v-if="!isValidStatus(row)"
                class="display-text"
                style="width: 27px">
                --
              </div>
              <div
                v-else
                class="rotate-table-column">
                <BkPopover
                  placement="bottom"
                  :popover-delay="[500, 50]"
                  theme="light"
                  :width="780">
                  <div class="display-text">{{ getStatusInfo(row).title }}: {{ getDutyPeoples(row) }}</div>
                  <template #content>
                    <RenderRotateTable :data="row" />
                  </template>
                </BkPopover>
              </div>
            </template>
          </TableColumn>
          <TableColumn
            col-key="effective_time"
            :title="t('生效时间')"
            :width="240">
            <template #default="{ row }: { row: DutyRuleModel }">
              <span>{{ row.effectiveTimeDisplay }}</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="update_at"
            :title="t('更新时间')"
            :width="240">
            <template #default="{ row }: { row: DutyRuleModel }">
              <span>{{ row.updateAtDisplay }}</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="updater"
            :title="t('更新人')"
            :width="120">
          </TableColumn>
          <TableColumn
            col-key="is_enabled"
            :title="t('启停')"
            :width="80">
            <template #default="{ row }: { row: DutyRuleModel }">
              <BkPopConfirm
                :content="t('停用后，所有的业务将会停用该策略，请谨慎操作！')"
                :is-show="showTipMap[row.id]"
                placement="bottom"
                :title="t('确认停用该策略？')"
                trigger="manual"
                width="320"
                @cancel="() => handleCancelConfirm(row)"
                @confirm="() => handleClickConfirm(row)">
                <AuthSwitcher
                  v-model="row.is_enabled"
                  action-id="duty_rule_manage"
                  :before-change="(isEnable: boolean) => enableRequestHandler(isEnable, row)"
                  :permission="row.permission.duty_rule_manage"
                  :resource="activeDbType"
                  size="small"
                  theme="primary" />
              </BkPopConfirm>
            </template>
          </TableColumn>
          <TableColumn
            col-key="row-operation"
            fixed="right"
            :title="t('操作')"
            :width="140">
            <template #default="{ row }: { row: DutyRuleModel }">
              <div class="operate-box">
                <AuthButton
                  action-id="duty_rule_manage"
                  :permission="row.permission.duty_rule_manage"
                  :resource="activeDbType"
                  text
                  theme="primary"
                  @click="() => handleOperate('edit', row)">
                  {{ t('编辑') }}
                </AuthButton>
                <AuthButton
                  action-id="duty_rule_manage"
                  :permission="row.permission.duty_rule_manage"
                  :resource="activeDbType"
                  text
                  theme="primary"
                  @click="() => handleOperate('clone', row)">
                  {{ t('克隆') }}
                </AuthButton>
                <AuthButton
                  v-if="!row.is_enabled"
                  action-id="duty_rule_manage"
                  :permission="row.permission.duty_rule_manage"
                  :resource="activeDbType"
                  text
                  theme="primary"
                  @click="() => handleDelete(row)">
                  {{ t('删除') }}
                </AuthButton>
              </div>
            </template>
          </TableColumn>
        </DbTable>
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
<script setup lang="ts">
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
  import DbTable from '@components/db-table/IndexNew.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import EditRule from '../edit-rule/Index.vue';

  import PriorityInput from './components/PriorityInput.vue';
  import RenderRotateTable from './components/RenderRotateTable.vue';

  interface Props {
    activeDbType: string;
  }

  const props = defineProps<Props>();

  const enum RuleStatus {
    ACTIVE = 'ACTIVE', // 当前生效
    EXPIRED = 'EXPIRED', // 已失效
    NOT_ACTIVE = 'NOT_ACTIVE', // 未生效
    TERMINATED = 'TERMINATED', // 已停用
  }

  const { t } = useI18n();

  const dataSource = (params: ServiceParameters<typeof queryDutyRuleList>) =>
    queryDutyRuleList(
      Object.assign(params, {
        db_type: props.activeDbType,
      }),
      {
        permission: 'catch',
      },
    );

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
    [RuleStatus.EXPIRED]: {
      label: t('已失效'),
      theme: '',
      title: t('已值班人'),
    },
    [RuleStatus.NOT_ACTIVE]: {
      label: t('未生效'),
      theme: 'info',
      title: t('待值班人'),
    },
    [RuleStatus.TERMINATED]: {
      label: t('已停用'),
      theme: '',
      title: t('待值班人'),
    },
  } as const;

  const getStatusInfo = (row: DutyRuleModel) => statusMap[row.status as RuleStatus];

  const isValidStatus = (row: DutyRuleModel) => row.status in statusMap;

  const getPriorityTheme = (row: DutyRuleModel) => {
    if (sortedPriority.value.length === 3) {
      const [largest, medium, least] = sortedPriority.value;
      if (row.priority === largest) {
        return 'danger';
      }
      if (row.priority === medium) {
        return 'warning';
      }
      if (row.priority === least) {
        return 'success';
      }
    }
    return '';
  };

  const getBizConfigDisplay = (row: DutyRuleModel) => {
    if (row.biz_config_display.include) {
      return row.biz_config_display.include.map((biz) => biz.bk_biz_name).join(' , ');
    }
    if (row.biz_config_display.exclude) {
      return `${t('全部业务')} (${t('排除业务')} : ${row.biz_config_display.exclude.map((biz) => biz.bk_biz_name).join(' , ')}) `;
    }
    return t('全部业务');
  };

  const getDutyPeoples = (row: DutyRuleModel) => {
    const peopleSet = row.duty_arranges.reduce((result, item) => {
      item.members.forEach((member) => {
        result.add(member);
      });
      return result;
    }, new Set<string>());
    return [...peopleSet].join(' , ');
  };

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

  watch(
    () => props.activeDbType,
    (type) => {
      if (type) {
        setTimeout(() => {
          fetchHostNodes();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const updateRowClass = ({ row }: { row: Record<string, any> }) =>
    (row as DutyRuleModel).isNewCreated ? 'is-new' : '';

  const fetchHostNodes = async () => {
    isTableLoading.value = true;
    try {
      await tableRef.value.fetchData({});
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
      });

      if (updateResult.priority === priority) {
        // 设置成功
        messageSuccess(t('优先级设置成功'));
      }
      runGetPriorityDistinct();
      window.changeConfirm = false;
    } finally {
      Object.assign(row, {
        is_show_edit: false,
        priority,
      });
    }
  };

  const enableRequestHandler = (isEnable: boolean, row: DutyRuleModel) =>
    new Promise((resolve, reject) => {
      enableRequestHandlerResolver = resolve;
      enableRequestHandlerRejecter = reject;
      if (isEnable) {
        updatePartialDutyRule(row.id, {
          is_enabled: true,
        })
          .then(() => {
            resolve(true);
            messageSuccess(t('启用成功'));
          })
          .catch(() => {
            reject();
          });
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
    existedNames.value = tableRef.value.getData().map((item: { name: string }) => item.name);
    currentRowData.value = row;
    pageType.value = type;
    isShowEditRuleSideSilder.value = true;
  };

  const handleDelete = async (row: DutyRuleModel) => {
    InfoBox({
      onConfirm: async () => {
        await deleteDutyRule({ id: row.id });
        fetchHostNodes();
      },
      subTitle: t('重置 Secure Key,需自定修改 Template 中的地址字段！'),
      title: t('确认删除该轮值?'),
      width: 450,
    });
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
