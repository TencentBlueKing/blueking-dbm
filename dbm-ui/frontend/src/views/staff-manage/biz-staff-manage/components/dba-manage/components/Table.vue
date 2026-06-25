<template>
  <div class="biz-staff-manage-dba-table">
    <template v-if="!isBatchEdit">
      <BkAlert :title="t('当前业务各组件类型的 DBA 负责人配置。如需修改请点击编辑。')" />
      <div class="top-box mt-16">
        <AuthButton
          action-id="dba_admin_edit"
          theme="primary"
          @click="handleBatchEdit">
          {{ t('批量编辑') }}
        </AuthButton>
        <MemberSelector
          v-model="searchUsers"
          :mutiple="false"
          style="width: 560px; margin-left: auto"
          @change="handleSearchUsersChange" />
      </div>
    </template>
    <div ref="tableWrapper">
      <DbForm
        ref="form"
        form-type="vertical"
        :label-width="0"
        :model="formData"
        :scroll-align-to-top="false">
        <PrimaryTable
          ref="table"
          class="dba-table mt-20"
          :data="formData.filterTableData"
          :max-height="tableMaxHeight"
          :row-class-name="rowClassName"
          row-key="db_type">
          <TableColumn
            col-key="db_type_display"
            :title="t('组件类型')"
            :width="160">
            <template #default="{ row }: { row: IRowData }">
              <div class="db-type">
                <DbIcon
                  class="db-type-icon"
                  :type="DBTypeInfos[row.db_type as DBTypes].icon" />
                <span class="ml-4">{{ row.db_type_display }}</span>
                <DbIcon
                  v-if="!row.is_edit && isPrimaryAndStanbySame(row)"
                  v-bk-tooltips="
                    t('主 DBA 与 备DBA 相同（均为{user}），该人员不在时审批可能无人处理', {
                      user: `${row.primary_dba}（${userDataMap[row.primary_dba]}）`,
                    })
                  "
                  class="ml-4 mt-4"
                  style="font-size: 14px; color: #f59500; cursor: pointer"
                  type="early-warning" />
                <BkButton
                  v-if="row.users.length > 0 || defaultAdminsDataMap[row.db_type as DBTypes].users.length > 0"
                  v-bk-tooltips="t('复制该行所有DBA')"
                  class="copy-btn"
                  text
                  theme="primary"
                  @click="() => handleCopyRow(row)">
                  <DbIcon type="copy" />
                </BkButton>
              </div>
            </template>
          </TableColumn>
          <TableColumn
            col-key="primary-dba"
            :width="250">
            <template #title>
              <div style="display: flex; align-items: center">
                <span>{{ t('主 DBA') }}</span>
                <!-- <BkTag
                  class="ml-4"
                  size="small"
                  :theme="dbaRoleTypesInfo[DBARoleTypes.PRIMARY_DBA].tagTheme">
                  {{ dbaRoleTypesInfo[DBARoleTypes.PRIMARY_DBA].tagText }}
                </BkTag> -->
                <BatchEdit
                  v-if="isBatchEdit"
                  class="ml-4"
                  field="primary_dba_edit"
                  :label="t('主 DBA')"
                  :multiple="false"
                  @batch-edit="handleBatchEditColumn" />
              </div>
            </template>
            <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
              <DbFormItem
                v-if="row.is_edit"
                error-display-type="tooltips"
                :property="`filterTableData.${rowIndex}.primary_dba_edit`"
                :required="row.standby_dba_edit.length > 0 || row.level2_dba_edit.length > 0">
                <div class="member-selector-wrapper">
                  <MemberSelector
                    v-model="row.primary_dba_edit"
                    class="member-selector"
                    :multiple="false"
                    @change="() => handleMemberChange(`filterTableData.${rowIndex}.primary_dba_edit`)" />
                  <BkButton
                    v-bk-tooltips="t('主备互换')"
                    class="ml-16"
                    text
                    @click="handleSwitchPrimaryAndStandby(row, rowIndex)">
                    <DbIcon
                      class="switch-icon"
                      type="qiehuan-2" />
                  </BkButton>
                </div>
                <div
                  v-if="isEditPrimaryAndStanbySame(row)"
                  class="member-selector-tip">
                  <DbIcon
                    class="mr-4"
                    type="attention" />
                  <span>{{ t('主备 DBA 为同一人，建议设置不同人员') }}</span>
                </div>
              </DbFormItem>
              <template v-else>
                <div v-if="row.primary_dba">
                  <span>{{ row.primary_dba }}（{{ userDataMap[row.primary_dba] }}）</span>
                  <!-- <BkButton
                    class="copy-btn"
                    text
                    theme="primary"
                    @click="() => handleCopy([row.primary_dba])">
                    <DbIcon type="copy" />
                  </BkButton> -->
                </div>
                <template v-else>
                  <div v-if="defaultAdminsDataMap[row.db_type as DBTypes]?.users?.length">
                    <div class="fallback-dba">
                      <span class="allback-dba-value">{{ defaultAdminsDataMap[row.db_type as DBTypes].users[0] }}</span>
                      <span class="allback-dba-alert">（{{ t('兜底') }}）</span>
                      <!-- <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([defaultAdminsDataMap[row.db_type as DBTypes].users[0]])">
                        <DbIcon type="copy" />
                      </BkButton> -->
                    </div>
                  </div>
                  <span v-else>--</span>
                </template>
              </template>
            </template>
          </TableColumn>
          <TableColumn
            col-key="standby-dba"
            :width="250">
            <template #title>
              <div style="display: flex; align-items: center">
                <span>{{ t('备 DBA') }}</span>
                <!-- <BkTag
                  class="ml-4"
                  size="small"
                  :theme="dbaRoleTypesInfo[DBARoleTypes.BACKUP_DBA].tagTheme">
                  {{ dbaRoleTypesInfo[DBARoleTypes.BACKUP_DBA].tagText }}
                </BkTag> -->
                <BatchEdit
                  v-if="isBatchEdit"
                  class="ml-4"
                  field="standby_dba_edit"
                  :label="t('备 DBA')"
                  :multiple="false"
                  @batch-edit="handleBatchEditColumn" />
              </div>
            </template>
            <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
              <DbFormItem
                v-if="row.is_edit"
                error-display-type="tooltips"
                :property="`filterTableData.${rowIndex}.standby_dba_edit`"
                :required="row.primary_dba_edit.length > 0 || row.level2_dba_edit.length > 0">
                <MemberSelector
                  v-model="row.standby_dba_edit"
                  :multiple="false"
                  @change="() => handleMemberChange(`filterTableData.${rowIndex}.standby_dba_edit`)" />
                <div
                  v-if="isEditPrimaryAndStanbySame(row)"
                  class="member-selector-tip">
                  <DbIcon
                    class="mr-4"
                    type="attention" />
                  <span>{{ t('主备 DBA 为同一人，建议设置不同人员') }}</span>
                </div>
              </DbFormItem>
              <template v-else>
                <div v-if="row.standby_dba">
                  <span>{{ row.standby_dba }}（{{ userDataMap[row.standby_dba] }}）</span>
                  <!-- <BkButton
                    class="copy-btn"
                    text
                    theme="primary"
                    @click="() => handleCopy([row.standby_dba])">
                    <DbIcon type="copy" />
                  </BkButton> -->
                </div>
                <template v-else>
                  <div v-if="defaultAdminsDataMap[row.db_type as DBTypes]?.users?.length">
                    <div class="fallback-dba">
                      <span class="allback-dba-value">{{ defaultAdminsDataMap[row.db_type as DBTypes].users[0] }}</span>
                      <span class="allback-dba-alert">（{{ t('兜底') }}）</span>
                      <!-- <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([defaultAdminsDataMap[row.db_type as DBTypes].users[0]])">
                        <DbIcon type="copy" />
                      </BkButton> -->
                    </div>
                  </div>
                  <span v-else>--</span>
                </template>
              </template>
            </template>
          </TableColumn>
          <TableColumn
            col-key="level2_dba"
            :min-width="300">
            <template #title>
              <div style="display: flex; align-items: center">
                <span>{{ t('二线 DBA') }}</span>
                <!-- <BkTag
                  class="ml-4"
                  size="small"
                  :theme="dbaRoleTypesInfo[DBARoleTypes.LEVEL2_DBA].tagTheme">
                  {{ dbaRoleTypesInfo[DBARoleTypes.LEVEL2_DBA].tagText }}
                </BkTag> -->
                <BatchEdit
                  v-if="isBatchEdit"
                  class="ml-4"
                  field="level2_dba_edit"
                  :label="t('二线 DBA')"
                  @batch-edit="handleBatchEditColumn" />
              </div>
            </template>
            <template #default="{ row }: { row: IRowData }">
              <DbFormItem v-if="row.is_edit">
                <MemberSelector
                  v-model="row.level2_dba_edit"
                  fast-clear />
                <div
                  v-if="isEditPrimaryAndStanbySame(row)"
                  class="member-selector-tip" />
              </DbFormItem>
              <template v-else>
                <template v-if="row.users.length">
                  <div v-if="row.level2_dba.length > 0">
                    <TagBlock
                      :copy-data="row.level2_dba"
                      :data="row.level2_dba.map((item) => `${item}（${userDataMap[item]}）`)" />
                  </div>
                  <span v-else>--</span>
                </template>
                <template v-else>
                  <div v-if="defaultAdminsDataMap[row.db_type as DBTypes]?.users?.length">
                    <div class="fallback-dba">
                      <span class="allback-dba-value">{{ defaultAdminsDataMap[row.db_type as DBTypes].users[0] }}</span>
                      <span class="allback-dba-alert">（{{ t('兜底') }}）</span>
                      <!-- <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([defaultAdminsDataMap[row.db_type as DBTypes].users[0]])">
                        <DbIcon type="copy" />
                      </BkButton> -->
                    </div>
                  </div>
                  <span v-else>--</span>
                </template>
              </template>
            </template>
          </TableColumn>
          <TableColumn
            v-if="!isBatchEdit"
            col-key="status"
            :title="t('状态')"
            width="100">
            <template #default="{ row }: { row: IRowData }">
              <BkTag
                v-if="row.users.length"
                theme="success">
                {{ t('已分配') }}
              </BkTag>
              <template v-else>
                <BkTag
                  v-if="defaultAdminsDataMap[row.db_type as DBTypes].users.length > 0"
                  theme="warning">
                  {{ t('待分配') }}
                </BkTag>
                <BkTag
                  v-else
                  theme="danger">
                  {{ t('默认配置缺失') }}
                </BkTag>
              </template>
            </template>
          </TableColumn>
          <TableColumn
            v-if="!isBatchEdit"
            col-key="update_at"
            :title="t('更新时间')"
            width="200">
            <template #default="{ row }: { row: IRowData }">
              {{ utcDisplayTime(row.update_at) || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            v-if="!isBatchEdit"
            col-key="updater"
            :title="t('更新人')"
            :width="120">
            <template #default="{ row }: { row: IRowData }">
              {{ row.updater || '--' }}
            </template>
          </TableColumn>
          <TableColumn
            v-if="!isBatchEdit"
            col-key="operation"
            :title="t('操作')"
            width="100">
            <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
              <template v-if="row.is_edit">
                <BkButton
                  :loading="rowUpdateLoading"
                  text
                  theme="primary"
                  @click="() => handleRowSave(row)">
                  {{ t('保存') }}
                </BkButton>
                <BkButton
                  class="ml-16"
                  :disabled="rowUpdateLoading"
                  text
                  theme="primary"
                  @click="() => handleRowCancel(row, rowIndex)">
                  {{ t('取消') }}
                </BkButton>
              </template>
              <AuthButton
                v-else
                action-id="dba_admin_edit"
                :permission="row.users.length > 0 ? row.permission.dba_admin_edit : 'normal'"
                text
                theme="primary"
                @click="() => handleRowEdit(row, rowIndex)">
                {{ t('编辑') }}
              </AuthButton>
            </template>
          </TableColumn>
          <template #empty>
            <BkException
              v-if="activeTopTab === 'apply'"
              scene="part"
              :title="t('当前业务尚未部署任何 DB 组件')"
              type="empty">
              <template #description>
                <I18nT
                  keypath="前往 n 页面部署数据库 DBA 管理"
                  tag="span">
                  <template #n>
                    <RouterLink
                      :to="{
                        name: 'BussinessServiceApply',
                      }">
                      {{ t('部署申请') }}
                    </RouterLink>
                  </template>
                </I18nT>
              </template>
            </BkException>
            <BkException
              v-else
              :description="t('暂无数据')"
              scene="part"
              style="font-size: 12px"
              type="empty" />
          </template>
        </PrimaryTable>
      </DbForm>
    </div>
    <div v-if="isBatchEdit">
      <BkButton
        v-bk-tooltips="{
          content: t('当前无变更，请先修改内容'),
          disabled: changedDataList.length > 0,
        }"
        class="w-88 mt-16"
        :disabled="changedDataList.length === 0"
        :loading="batchUpdateLoading"
        theme="primary"
        @click="() => handleBatchSave()">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88 ml-16"
        :disabled="batchUpdateLoading"
        @click="() => handleBatchCancel()">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DBAdminModel from '@services/model/db-admin/db-admin';
  import { updateAdmins } from '@services/source/dbadmin';

  import { DBAOperateTypes, DBARoleTypes, DBTypeInfos, DBTypes } from '@common/const';

  import MemberSelector from '@components/db-member-selector/index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import BatchEdit from '@views/staff-manage/common/BatchEdit.vue';

  import { execCopy, getOffset, messageSuccess, utcDisplayTime } from '@utils';

  interface Props {
    activeTopTab: 'apply' | 'unapply';
    data: DBAdminModel[];
    defaultAdminsDataMap: Record<string, DBAdminModel>;
    userDataMap: Record<string, string>;
  }

  type Emits = (e: 'suceess') => void;

  type IRowData = {
    is_edit: boolean;
    level2_dba: string[];
    level2_dba_edit: string[];
    primary_dba: string;
    primary_dba_edit: string[];
    standby_dba: string;
    standby_dba_edit: string[];
  } & DBAdminModel;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rootRef = useTemplateRef('tableWrapper');
  const formRef = useTemplateRef('form');

  const tableMaxHeight = ref<number | 'auto'>('auto');
  const searchUsers = ref<string[]>([]);
  const originalTableData = ref<IRowData[]>([]);
  const formData = ref({
    filterTableData: [] as IRowData[],
  });

  const isBatchEdit = computed(
    () =>
      formData.value.filterTableData.length > 0 &&
      formData.value.filterTableData.length === formData.value.filterTableData.filter((item) => item.is_edit).length,
  );
  const changedDataList = computed(() =>
    formData.value.filterTableData.filter(
      (item) =>
        !_.isEqual(item.primary_dba ? [item.primary_dba] : [], item.primary_dba_edit) ||
        !_.isEqual(item.standby_dba ? [item.standby_dba] : [], item.standby_dba_edit) ||
        !_.isEqual(_.sortBy(item.level2_dba), _.sortBy(item.level2_dba_edit)),
    ),
  );

  const { loading: batchUpdateLoading, run: runBatchUpdateAdmins } = useRequest(updateAdmins, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('suceess');
    },
  });

  const { loading: rowUpdateLoading, run: runRowUpdateAdmins } = useRequest(updateAdmins, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      emits('suceess');
    },
  });

  watch(
    () => props.data,
    () => {
      searchUsers.value = [];
      originalTableData.value = props.data.map((item) => {
        const [primaryDBA, standbyDBA, ...level2DBA] = item.users;
        return {
          ...item,
          is_edit: false,
          level2_dba: level2DBA,
          level2_dba_edit: _.cloneDeep(level2DBA),
          primary_dba: primaryDBA || '',
          primary_dba_edit: primaryDBA ? [primaryDBA] : [],
          standby_dba: standbyDBA || '',
          standby_dba_edit: standbyDBA ? [standbyDBA] : [],
        };
      });
      formData.value.filterTableData = _.cloneDeep(originalTableData.value);
    },
    {
      immediate: true,
    },
  );

  watch(isBatchEdit, () => {
    setTableMaxHeight();
  });

  const rowClassName = ({ row }: { row: IRowData }) => {
    return !row.is_edit && isPrimaryAndStanbySame(row) ? 'warning-row' : '';
  };

  const handleSwitchPrimaryAndStandby = (row: IRowData, rowIndex: number) => {
    const { primary_dba_edit: primaryDBA, standby_dba_edit: standbyDBA } = row;
    formData.value.filterTableData[rowIndex] = Object.assign(row, {
      primary_dba_edit: standbyDBA,
      standby_dba_edit: primaryDBA,
    });
  };

  const isPrimaryAndStanbySame = (row: IRowData) => {
    return row.primary_dba && row.standby_dba && row.primary_dba === row.standby_dba;
  };

  const isEditPrimaryAndStanbySame = (row: IRowData) => {
    return (
      row.primary_dba_edit.length > 0 &&
      row.standby_dba_edit.length > 0 &&
      row.primary_dba_edit[0] === row.standby_dba_edit[0]
    );
  };

  const handleMemberChange = (property: string) => {
    formRef.value?.validate(property);
  };

  const handleSearchUsersChange = (users: string[]) => {
    if (users.length) {
      const searchUsersMap = Object.fromEntries(users.map((item) => [item, true]));
      formData.value.filterTableData = _.cloneDeep(
        originalTableData.value.filter((row) => {
          return [
            ...(row.primary_dba ? [row.primary_dba] : []),
            ...(row.standby_dba ? [row.standby_dba] : []),
            ...row.level2_dba_edit,
          ].some((item) => searchUsersMap[item]);
        }),
      );
    } else {
      formData.value.filterTableData = _.cloneDeep(originalTableData.value);
    }
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.value.filterTableData = formData.value.filterTableData.map((item) => ({
      ...item,
      [field]: value,
    }));
  };

  const handleBatchEdit = () => {
    formData.value.filterTableData = formData.value.filterTableData.map((row) => ({
      ...row,
      is_edit: true,
      level2_dba_edit: _.cloneDeep(row.level2_dba),
      primary_dba_edit: row.primary_dba ? [row.primary_dba] : [],
      standby_dba_edit: row.standby_dba ? [row.standby_dba] : [],
    }));
  };

  const handleBatchSave = async () => {
    await formRef.value!.validate();
    const operates = changedDataList.value
      .flatMap((row) => {
        return [
          {
            after: row.primary_dba_edit.join(','),
            before: [row.primary_dba].join(','),
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            db_type: row.db_type as DBTypes,
            role: DBARoleTypes.PRIMARY_DBA,
            type: DBAOperateTypes.DBA_CHANGE,
          },
          {
            after: row.standby_dba_edit.join(','),
            before: [row.standby_dba].join(','),
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            db_type: row.db_type as DBTypes,
            role: DBARoleTypes.BACKUP_DBA,
            type: DBAOperateTypes.DBA_CHANGE,
          },
          {
            after: row.level2_dba_edit.join(','),
            before: row.level2_dba.join(','),
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            db_type: row.db_type as DBTypes,
            role: DBARoleTypes.LEVEL2_DBA,
            type: DBAOperateTypes.DBA_CHANGE,
          },
        ];
      })
      .filter((item) => item.after !== item.before);

    runBatchUpdateAdmins({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      db_admins: changedDataList.value.map((item) => {
        return {
          db_type: item.db_type,
          db_type_display: item.db_type_display,
          users: [...item.primary_dba_edit, ...item.standby_dba_edit, ...item.level2_dba_edit],
        };
      }),
      operates,
    });
  };

  const handleBatchCancel = () => {
    formData.value.filterTableData = formData.value.filterTableData.map((item) => ({
      ...item,
      is_edit: false,
    }));
  };

  const handleRowEdit = (row: IRowData, rowIndex: number) => {
    let tableList = formData.value.filterTableData;

    tableList = tableList.map((item) => ({
      ...item,
      is_edit: false,
      level2_dba_edit: _.cloneDeep(item.level2_dba),
      primary_dba_edit: item.primary_dba ? [item.primary_dba] : [],
      standby_dba_edit: item.standby_dba ? [item.standby_dba] : [],
    }));
    tableList[rowIndex].is_edit = true;

    formData.value.filterTableData = tableList;
  };

  const handleRowSave = async (row: IRowData) => {
    await formRef.value!.validate();
    const operates = [
      {
        after: row.primary_dba_edit.join(','),
        before: [row.primary_dba].join(','),
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: row.db_type as DBTypes,
        role: DBARoleTypes.PRIMARY_DBA,
        type: DBAOperateTypes.DBA_CHANGE,
      },
      {
        after: row.standby_dba_edit.join(','),
        before: [row.standby_dba].join(','),
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: row.db_type as DBTypes,
        role: DBARoleTypes.BACKUP_DBA,
        type: DBAOperateTypes.DBA_CHANGE,
      },
      {
        after: row.level2_dba_edit.join(','),
        before: row.level2_dba.join(','),
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: row.db_type as DBTypes,
        role: DBARoleTypes.LEVEL2_DBA,
        type: DBAOperateTypes.DBA_CHANGE,
      },
    ].filter((item) => item.after !== item.before);

    runRowUpdateAdmins({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      db_admins: [
        {
          db_type: row.db_type as DBTypes,
          db_type_display: row.db_type_display,
          users: [...row.primary_dba_edit, ...row.standby_dba_edit, ...row.level2_dba_edit],
        },
      ],
      operates,
    });
  };

  const handleRowCancel = (row: IRowData, rowIndex: number) => {
    formData.value.filterTableData[rowIndex].is_edit = false;
  };

  const handleCopyRow = (row: IRowData) => {
    if (row.users.length > 0) {
      execCopy(_.uniq([row.primary_dba, row.standby_dba, ...row.level2_dba]).join('；'));
    } else {
      const defaultDba = props.defaultAdminsDataMap[row.db_type as DBTypes].users[0];
      execCopy(defaultDba);
    }
  };

  // const handleCopy = (userList: string[]) => {
  //   if (userList.length < 1) {
  //     messageWarn(t('没有可复制 DBA'));
  //     return;
  //   }
  //   execCopy(
  //     userList.join('\n'),
  //     t('复制成功，共n条', {
  //       n: userList.length,
  //     }),
  //   );
  // };

  const setTableMaxHeight = () => {
    nextTick(() => {
      tableMaxHeight.value =
        window.innerHeight - getOffset(rootRef.value as HTMLElement).top - (isBatchEdit.value ? 48 : 0) - 20 - 20;
    });
  };

  onMounted(() => {
    setTableMaxHeight();
  });
</script>

<style lang="less">
  .biz-staff-manage-dba-table {
    padding: 16px 24px;

    .top-box {
      display: flex;
      align-items: center;
    }

    .db-type {
      display: flex;
      align-items: center;

      .db-type-icon {
        font-size: 16px;

        &.db-icon-mysql {
          color: #3a84ff;
        }

        &.db-icon-redis {
          color: #ea3636;
        }

        &.db-icon-es {
          color: #3c9c48;
        }

        &.db-icon-kafka {
          color: #333;
        }

        &.db-icon-mongo-db {
          color: #3c9c48;
        }

        &.db-icon-doris {
          color: #3c9c48;
        }

        &.db-icon-hdfs {
          color: #f59500;
        }

        &.db-icon-influxdb {
          color: #3a84ff;
        }

        &.db-icon-pulsar {
          color: #2c2cea;
        }

        &.db-icon-cluster {
          color: #333;
        }

        &.db-icon-sqlserver {
          color: #ea3636;
        }
      }
    }

    .dba-table {
      .warning-row {
        background-color: #fdf4e8;
      }

      .fallback-dba {
        .allback-dba-value {
          color: #c4c6cc;
        }

        .allback-dba-alert {
          color: #f8b64f;
        }
      }

      tbody {
        tr {
          &:hover {
            .copy-btn {
              display: inline !important;
            }
          }
        }
      }

      .copy-btn {
        display: none;
        margin-top: 1px;
        margin-left: 4px;
        // color: @primary-color;
        cursor: pointer;
      }

      .bk-form-item {
        &.is-error {
          .db-member-selector-copy {
            right: 24px;
          }
        }
      }

      .member-selector-wrapper {
        display: flex;
        align-items: center;

        .member-selector {
          flex: 1;
          min-width: 0;
        }

        .switch-icon {
          flex-shrink: 0;
          font-size: 20px;
          color: #c4c6cc;

          &:hover {
            color: #4d4f56;
          }
        }
      }

      .member-selector-tip {
        height: 20px;
        line-height: 20px;
        color: #fe9c00;
      }
    }
  }
</style>
