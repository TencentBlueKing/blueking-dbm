<template>
  <div class="global-staff-manage-db-type">
    <BkAlert :title="t('待分配 状态的业务由默认 DBA 兜底负责，如需指定专人可通过编辑或批量设置完成。')" />
    <div class="dbtype-action-bar mt-16">
      <BkRadioGroup
        v-model="status"
        class="mr-8"
        type="capsule"
        @change="handleQuickSearchChange">
        <BkRadioButton label="assigned">{{ t('已分配') }}({{ countMap.allocateCount }})</BkRadioButton>
        <BkRadioButton label="unassigned">{{ t('待分配') }}({{ countMap.defaultCount }})</BkRadioButton>
      </BkRadioGroup>
      <BkButton
        v-bk-tooltips="{
          content: t('请先选择业务'),
          disabled: isSelected,
        }"
        :disabled="!isSelected"
        @click="handleBatchUpdate">
        {{ t('批量设置') }}
      </BkButton>
      <BkButton
        v-if="status === 'assigned'"
        v-bk-tooltips="{
          content: t('请先选择业务'),
          disabled: isSelected,
        }"
        class="ml-8"
        :disabled="!isSelected"
        @click="handleBatchReplace">
        {{ t('批量替换') }}
      </BkButton>
      <BkButton
        v-if="status === 'assigned'"
        v-bk-tooltips="{
          content: t('请先选择业务'),
          disabled: isSelected,
        }"
        class="ml-8"
        :disabled="!isSelected"
        @click="handleBatchAppendL2DBA">
        {{ t('批量追加二线') }}
      </BkButton>
      <BkButton
        v-if="status === 'assigned'"
        v-bk-tooltips="{
          content: t('请先选择业务'),
          disabled: isSelected,
        }"
        class="ml-8"
        :disabled="!isSelected"
        @click="handleBatchRemoveL2DBA">
        {{ t('批量移除二线') }}
      </BkButton>
      <div class="bar-right">
        <DbQuickSearch
          v-model="searchValue"
          :data="quickSearchData"
          parse-url
          :placeholder="t('请输入或选择条件搜索')"
          style="width: 500px; margin-left: auto"
          @change="handleQuickSearchChange" />
      </div>
    </div>
    <div ref="tableWrapper">
      <BkLoading :loading="isLoading">
        <BkForm
          ref="form"
          :label-width="0"
          :model="formData">
          <PrimaryTable
            ref="table"
            class="dba-table mt-20"
            :data="formData.tableData"
            :max-height="tableMaxHeight"
            row-key="bk_biz_id"
            :selected-row-keys="selectedRowKeys"
            @select-change="handleSelectChange">
            <TableColumn
              col-key="row-select"
              fixed="left"
              type="multiple"
              :width="40">
            </TableColumn>
            <TableColumn
              col-key="bk_biz_id"
              fixed="left"
              :title="t('业务 ID')"
              width="160">
              <template #default="{ row }: { row: BizDbaModel }">
                {{ row.bk_biz_id }}
                <BkButton
                  v-if="row.isAssigned || defaultUserData"
                  class="copy-btn"
                  text
                  theme="primary"
                  @click="() => handleCopyRow(row)">
                  <DbIcon type="copy" />
                </BkButton>
              </template>
            </TableColumn>
            <TableColumn
              col-key="name"
              :title="t('业务名称')"
              width="160">
            </TableColumn>
            <TableColumn
              col-key="english_name"
              :title="t('业务代号')"
              width="160">
            </TableColumn>
            <TableColumn
              col-key="tags"
              :title="t('标签')"
              :width="180">
              <template #default="{ row }: { row: BizDbaModel }">
                <TagList
                  v-if="row.tags.length"
                  :list="row.tags.map((tagItem) => ({ label: tagItem.value, value: tagItem.id }))" />
                <span v-else>--</span>
              </template>
            </TableColumn>
            <TableColumn
              col-key="primary-dba"
              :min-width="260">
              <template #title>
                <span>{{ t('主 DBA') }}</span>
                <!-- <BkTag
                  class="ml-4"
                  size="small"
                  :theme="dbaRoleTypesInfo[DBARoleTypes.PRIMARY_DBA].tagTheme">
                  {{ dbaRoleTypesInfo[DBARoleTypes.PRIMARY_DBA].tagText }}
                </BkTag> -->
              </template>
              <template #default="{ row, rowIndex }: { row: BizDbaModel; rowIndex: number }">
                <BkFormItem
                  v-if="row.is_edit"
                  error-display-type="tooltips"
                  :property="`tableData.${rowIndex}.primary_dba_edit`"
                  required>
                  <MemberSelector
                    v-model="row.primary_dba_edit"
                    :multiple="false" />
                  <div
                    v-if="isPrimaryAndStanbySame(row)"
                    class="member-selector-tip">
                    <DbIcon
                      class="mr-4"
                      type="attention" />
                    <span>{{ t('主备 DBA 为同一人，建议设置不同人员') }}</span>
                  </div>
                </BkFormItem>
                <template v-else>
                  <TextOverflowLayout v-if="row.primary_dba">
                    <span>{{ row.primary_dba }}（{{ userDataMap[row.primary_dba] }}）</span>
                    <template #append>
                      <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([row.primary_dba])">
                        <DbIcon type="copy" />
                      </BkButton>
                    </template>
                  </TextOverflowLayout>
                  <template v-else-if="defaultUserData.username">
                    <div class="fallback-dba">
                      <span class="allback-dba-value">{{ defaultUserData.displayText }}</span>
                      <span class="allback-dba-alert">（{{ t('兜底') }}）</span>
                      <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([defaultUserData.username])">
                        <DbIcon type="copy" />
                      </BkButton>
                    </div>
                  </template>
                  <span v-else>--</span>
                </template>
              </template>
            </TableColumn>
            <TableColumn
              col-key="standby_dba"
              :min-width="260">
              <template #title>
                <span>{{ t('备 DBA') }}</span>
                <!-- <BkTag
                  class="ml-4"
                  size="small"
                  :theme="dbaRoleTypesInfo[DBARoleTypes.BACKUP_DBA].tagTheme">
                  {{ dbaRoleTypesInfo[DBARoleTypes.BACKUP_DBA].tagText }}
                </BkTag> -->
              </template>
              <template #default="{ row, rowIndex }: { row: BizDbaModel; rowIndex: number }">
                <BkFormItem
                  v-if="row.is_edit"
                  error-display-type="tooltips"
                  :property="`tableData.${rowIndex}.standby_dba_edit`"
                  required>
                  <MemberSelector
                    v-model="row.standby_dba_edit"
                    :multiple="false" />
                  <div
                    v-if="isPrimaryAndStanbySame(row)"
                    class="member-selector-tip">
                    <DbIcon
                      class="mr-4"
                      type="attention" />
                    <span>{{ t('主备 DBA 为同一人，建议设置不同人员') }}</span>
                  </div>
                </BkFormItem>
                <template v-else>
                  <TextOverflowLayout v-if="row.standby_dba">
                    <span>{{ row.standby_dba }}（{{ userDataMap[row.standby_dba] }}）</span>
                    <template #append>
                      <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([row.standby_dba])">
                        <DbIcon type="copy" />
                      </BkButton>
                    </template>
                  </TextOverflowLayout>
                  <template v-else-if="defaultUserData.username">
                    <div class="fallback-dba">
                      <span class="allback-dba-value">{{ defaultUserData.displayText }}</span>
                      <span class="allback-dba-alert">（{{ t('兜底') }}）</span>
                      <BkButton
                        class="copy-btn"
                        text
                        theme="primary"
                        @click="() => handleCopy([defaultUserData.username])">
                        <DbIcon type="copy" />
                      </BkButton>
                    </div>
                  </template>
                  <span v-else>--</span>
                </template>
              </template>
            </TableColumn>
            <TableColumn
              col-key="level2-dba"
              :min-width="300">
              <template #title>
                <span>{{ t('二线 DBA') }}</span>
                <!-- <BkTag
                  class="ml-4"
                  size="small"
                  :theme="dbaRoleTypesInfo[DBARoleTypes.LEVEL2_DBA].tagTheme">
                  {{ dbaRoleTypesInfo[DBARoleTypes.LEVEL2_DBA].tagText }}
                </BkTag> -->
              </template>
              <template #default="{ row }: { row: BizDbaModel }">
                <BkFormItem
                  v-if="row.is_edit"
                  required>
                  <MemberSelector
                    v-if="row.is_edit"
                    v-model="row.level2_dba_edit" />
                  <div
                    v-if="isPrimaryAndStanbySame(row)"
                    class="member-selector-tip" />
                </BkFormItem>
                <template v-else>
                  <template v-if="row.isAssigned">
                    <template v-if="row.level2_dba.length > 0">
                      <TagBlock
                        :copy-data="row.level2_dba"
                        copyenable
                        :data="row.level2_dba.map((item) => `${item}（${userDataMap[item]}）`)" />
                    </template>
                    <span v-else>--</span>
                  </template>
                  <template v-else>
                    <template v-if="defaultUserData.username">
                      <div class="fallback-dba">
                        <span class="allback-dba-value">{{ defaultUserData.displayText }}</span>
                        <span class="allback-dba-alert">（{{ t('兜底') }}）</span>
                        <BkButton
                          class="copy-btn"
                          text
                          theme="primary"
                          @click="() => handleCopy([defaultUserData.username])">
                          <DbIcon type="copy" />
                        </BkButton>
                      </div>
                    </template>
                    <span v-else>--</span>
                  </template>
                </template>
              </template>
            </TableColumn>
            <TableColumn
              col-key="status"
              :title="t('状态')"
              width="120">
              <template #default="{ row }: { row: BizDbaModel }">
                <BkTag
                  v-if="row.isAssigned"
                  theme="success">
                  {{ t('已分配') }}
                </BkTag>
                <BkTag
                  v-else-if="!defaultUserData"
                  theme="danger">
                  {{ t('默认配置缺失') }}
                </BkTag>
                <BkTag v-else>
                  {{ t('待分配') }}
                </BkTag>
              </template>
            </TableColumn>
            <TableColumn
              col-key="update_at"
              :title="t('更新时间')"
              :width="180">
              <template #default="{ row }: { row: BizDbaModel }">
                {{ row.updateAtTime || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="updater"
              :title="t('更新人')">
              <template #default="{ row }: { row: BizDbaModel }">
                {{ row.updater || '--' }}
              </template>
            </TableColumn>
            <TableColumn
              col-key="operation"
              fixed="right"
              :title="t('操作')"
              width="100">
              <template #default="{ row, rowIndex }: { row: BizDbaModel; rowIndex: number }">
                <template v-if="row.is_edit">
                  <BkButton
                    :loading="isUpdateAdminsLoading"
                    text
                    theme="primary"
                    @click="() => handleSave(row)">
                    {{ t('保存') }}
                  </BkButton>
                  <BkButton
                    class="ml-16"
                    :disabled="isUpdateAdminsLoading"
                    text
                    theme="primary"
                    @click="() => handleCancel(row, rowIndex)">
                    {{ t('取消') }}
                  </BkButton>
                </template>
                <BkButton
                  v-else
                  text
                  theme="primary"
                  @click="() => handleEdit(row, rowIndex)">
                  {{ t('编辑') }}
                </BkButton>
              </template>
            </TableColumn>
          </PrimaryTable>
          <div class="table-footer">
            <BkPagination
              v-bind="pagination"
              :layout="['total', 'limit', 'list']"
              @change="handlePageValueChange"
              @limit-change="handlePageLimitChange">
            </BkPagination>
          </div>
        </BkForm>
      </BkLoading>
    </div>
    <BatchUpdate
      v-model="isBatchUpdateShow"
      :db-type="activeTab"
      :selected="selected"
      :user-data-map="userDataMap"
      @success="handleClose" />
    <BatchReplace
      v-model="isBatchReplaceShow"
      :db-type="activeTab"
      :selected="selected"
      :user-data-map="userDataMap"
      @success="handleClose" />
    <BatchAppendL2DBA
      v-model="isBatchAppendL2DBAShow"
      :db-type="activeTab"
      :selected="selected"
      :user-data-map="userDataMap"
      @success="handleClose" />
    <BatchRemoveL2DBA
      v-model="isBatchRemoveL2DBAShow"
      :db-type="activeTab"
      :selected="selected"
      :user-data-map="userDataMap"
      @success="handleClose" />
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins, updateAdmins } from '@services/source/dbadmin';
  import { getUserList } from '@services/source/user';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { DBAOperateTypes, DBARoleTypes, DBTypeInfos, DBTypes } from '@common/const';

  import MemberSelector from '@components/db-member-selector/index.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { usePagination } from '@views/staff-manage/common/use-pagination.ts';

  import { execCopy, getOffset, messageSuccess, messageWarn } from '@utils';

  import BizDbaModel from './bizDba';
  import BatchAppendL2DBA from './components/BatchAppendL2DBA.vue';
  import BatchRemoveL2DBA from './components/BatchRemoveL2DBA.vue';
  import BatchReplace from './components/BatchReplace.vue';
  import BatchUpdate from './components/BatchUpdate.vue';
  import TagList from './components/TagList.vue';
  import { useQuickSearch } from './useQuickSearch';

  interface Props {
    activeTab: string;
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();
  const bizStore = useGlobalBizs();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();

  const status = ref<'assigned' | 'unassigned'>('assigned');
  const { handleFilterList, handleMergeSearchParams, quickSearchData, searchValue } = useQuickSearch(status);

  const formData = ref({
    tableData: [] as BizDbaModel[],
  });
  const bizList = ref<BizDbaModel[]>([]);
  const tableFilterData = ref<BizDbaModel[]>([]);
  const {
    currentPageDataList,
    onChange: handlePageValueChange,
    onLimitChange: handlePageLimitChange,
    pagination,
  } = usePagination<BizDbaModel>(tableFilterData);

  watch(currentPageDataList, () => {
    formData.value.tableData = currentPageDataList.value;
  });

  const formRef = useTemplateRef('form');
  const rootRef = useTemplateRef('tableWrapper');

  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isBatchUpdateShow = ref(false);
  const isBatchReplaceShow = ref(false);
  const isBatchAppendL2DBAShow = ref(false);
  const isBatchRemoveL2DBAShow = ref(false);
  const selectedRowKeys = ref<number[]>([]);
  const selected = shallowRef<BizDbaModel[]>([]);

  const getDefaultDbTypeAdmin = () => ({
    bk_biz_id: 0,
    db_type: props.activeTab,
    db_type_display: DBTypeInfos[props.activeTab as DBTypes].name,
    is_show: true,
    update_at: '',
    updater: '',
    users: [] as string[],
  });

  const isLoading = computed(
    () => isGetDefalutAdminsLoading.value || isGetBizAdminsLoading.value || isGetUserListLoading.value,
  );
  const isSelected = computed(() => selected.value.length > 0);
  const countMap = computed(() => {
    let allocateCount = 0;
    let defaultCount = 0;

    bizList.value.forEach((item) => {
      if (item.isAssigned) {
        allocateCount = allocateCount + 1;
      } else {
        defaultCount = defaultCount + 1;
      }
    });

    return {
      allocateCount,
      defaultCount,
    };
  });

  const defaultUserData = computed(() => {
    const user = defaultAdminData.value?.find((item) => item.db_type === props.activeTab)?.users?.[0];
    if (user) {
      return {
        displayText: `${user}（${userDataMap.value[user]}）`,
        username: user,
      };
    }
    return {
      displayText: '',
      username: '',
    };
  });
  const userDataMap = computed(() =>
    Object.fromEntries((userData.value?.results || []).map((item) => [item.username, item.display_name])),
  );

  const {
    data: defaultAdminData,
    loading: isGetDefalutAdminsLoading,
    run: runGetDefaultAdmins,
  } = useRequest(getAdmins, {
    manual: true,
  });

  const {
    data: bizAdminData,
    loading: isGetBizAdminsLoading,
    run: runGetBizAdmins,
  } = useRequest(getAdmins, {
    manual: true,
  });

  const { data: userData, loading: isGetUserListLoading } = useRequest(getUserList);

  const { loading: isUpdateAdminsLoading, run: runUpdateAdmins } = useRequest(updateAdmins, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      fetchData();
    },
  });

  watch(
    () => [bizStore.bizs, defaultAdminData.value, bizAdminData.value, userData.value],
    () => {
      if (!defaultAdminData.value || !bizAdminData.value || !userData.value) {
        bizList.value = [];
        return;
      }

      // const defaultDbTypeAdmin =
      //   defaultAdminData.value.find((item) => item.db_type === props.activeTab) || getDefaultDbTypeAdmin();
      const bizAdminMap = Object.fromEntries(bizAdminData.value.map((item) => [item.bk_biz_id, item]));

      bizList.value = bizStore.bizs.map((bizItem) => {
        // const adminItem = bizAdminMap[bizItem.bk_biz_id] || defaultDbTypeAdmin;
        const adminItem = bizAdminMap[bizItem.bk_biz_id] || getDefaultDbTypeAdmin();
        const [primaryDBA, standbyDBA, ...level2DBA] = adminItem.users;
        const bizDbaItem = {
          ...adminItem,
          ...bizItem,
          is_edit: false,
          level2_dba: level2DBA,
          level2_dba_edit: [],
          primary_dba: primaryDBA || '',
          primary_dba_edit: [],
          standby_dba: standbyDBA || '',
          standby_dba_edit: [],
        } as unknown as BizDbaModel;

        return new BizDbaModel(bizDbaItem);
      });

      handleQuickSearchChange();
    },
    {
      immediate: true,
    },
  );

  const fetchData = () => {
    runGetDefaultAdmins({
      bk_biz_id: 0,
    });
    runGetBizAdmins({
      db_type: props.activeTab as DBTypes,
    });
  };

  const handleQuickSearchChange = () => {
    selectedRowKeys.value = [];
    selected.value = [];

    const filterList = handleFilterList(bizList.value);
    router.replace({
      query: replaceSearchParams(handleMergeSearchParams(getSearchParams()), false),
    });
    tableFilterData.value = filterList;
  };

  const isPrimaryAndStanbySame = (row: BizDbaModel) => {
    return (
      row.primary_dba_edit.length > 0 &&
      row.standby_dba_edit.length > 0 &&
      row.primary_dba_edit[0] === row.standby_dba_edit[0]
    );
  };

  const handleBatchUpdate = () => {
    isBatchUpdateShow.value = true;
  };

  const handleBatchReplace = () => {
    isBatchReplaceShow.value = true;
  };

  const handleBatchAppendL2DBA = () => {
    isBatchAppendL2DBAShow.value = true;
  };

  const handleBatchRemoveL2DBA = () => {
    isBatchRemoveL2DBAShow.value = true;
  };

  const handleClose = () => {
    selectedRowKeys.value = [];
    selected.value = [];
    fetchData();
  };

  const handleSelectChange = (value: (string | number)[], { selectedRowData }: { selectedRowData: unknown[] }) => {
    selectedRowKeys.value = value as number[];
    selected.value = selectedRowData as BizDbaModel[];
  };

  const handleEdit = (row: BizDbaModel, rowIndex: number) => {
    let tableList = formData.value.tableData;

    tableList = tableList.map((item) => ({
      ...item,
      is_edit: false,
    }));
    tableList[rowIndex] = Object.assign(row, {
      is_edit: true,
      level2_dba_edit: _.cloneDeep(row.level2_dba),
      primary_dba_edit: row.primary_dba ? [row.primary_dba] : [],
      standby_dba_edit: row.standby_dba ? [row.standby_dba] : [],
    });

    formData.value.tableData = tableList;
  };

  const handleSave = (row: BizDbaModel) => {
    formRef.value!.validate().then(() => {
      const operates = [
        {
          after: row.primary_dba_edit.join(','),
          before: [row.primary_dba].join(','),
          bk_biz_id: row.bk_biz_id,
          db_type: props.activeTab as DBTypes,
          role: DBARoleTypes.PRIMARY_DBA,
          type: DBAOperateTypes.DBA_CHANGE,
        },
        {
          after: row.standby_dba_edit.join(','),
          before: [row.standby_dba].join(','),
          bk_biz_id: row.bk_biz_id,
          db_type: props.activeTab as DBTypes,
          role: DBARoleTypes.BACKUP_DBA,
          type: DBAOperateTypes.DBA_CHANGE,
        },
        {
          after: row.level2_dba_edit.join(','),
          before: row.level2_dba.join(','),
          bk_biz_id: row.bk_biz_id,
          db_type: props.activeTab as DBTypes,
          role: DBARoleTypes.LEVEL2_DBA,
          type: DBAOperateTypes.DBA_CHANGE,
        },
      ];
      runUpdateAdmins({
        bk_biz_id: row.bk_biz_id,
        db_admins: [
          {
            db_type: props.activeTab,
            db_type_display: DBTypeInfos[props.activeTab as DBTypes].name,
            users: [...row.primary_dba_edit, ...row.standby_dba_edit, ...row.level2_dba_edit],
          },
        ],
        operates: operates.filter((item) => item.after !== item.before),
      });
    });
  };

  const handleCancel = (row: BizDbaModel, rowIndex: number) => {
    formData.value.tableData[rowIndex].is_edit = false;
  };

  const handleCopyRow = (row: BizDbaModel) => {
    if (row.users.length > 0) {
      execCopy(_.uniq([row.primary_dba, row.standby_dba, ...row.level2_dba]).join('；'));
    } else {
      execCopy(defaultUserData.value.username);
    }
  };

  const handleCopy = (userList: string[]) => {
    if (userList.length < 1) {
      messageWarn(t('没有可复制 DBA'));
      return;
    }
    execCopy(
      userList.join('\n'),
      t('复制成功，共n条', {
        n: userList.length,
      }),
    );
  };

  onMounted(() => {
    fetchData();

    setTimeout(() => {
      tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 60 - 20 - 20;
    });
  });
</script>

<style lang="less">
  .global-staff-manage-db-type {
    padding: 16px 24px;

    .dbtype-action-bar {
      display: flex;
      align-items: center;

      .bar-right {
        display: flex;
        margin-left: auto;
      }
    }

    .dba-table {
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

      .member-selector-tip {
        height: 32px;
        color: #fe9c00;
      }

      .copy-btn {
        display: none;
        margin-top: 1px;
        margin-left: 4px;
        // color: @primary-color;
        cursor: pointer;
      }
    }

    .table-footer {
      position: relative;
      z-index: 1;
      display: flex;
      height: 60px;
      padding: 0 16px;
      margin-top: -1px;
      background: #fff;
      border-top: 1px solid var(--td-component-border);
      align-items: center;

      .bk-pagination {
        width: 100%;

        & > .is-last {
          margin-left: auto;
        }
      }
    }
  }
</style>
