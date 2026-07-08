<template>
  <div class="global-staff-manage-defalut-dba">
    <BkAlert :title="t('默认 DBA 按组件设置，作为兜底负责人，仅对该组件下待分配业务生效。')" />
    <AuthButton
      v-if="!isEdit"
      action-id="global_dba_admin_edit"
      class="mt-16"
      :disabled="isLoading"
      theme="primary"
      @click="() => handleEdit()">
      {{ t('编辑') }}
    </AuthButton>
    <div ref="tableWrapper">
      <BkLoading :loading="isLoading">
        <DbForm
          ref="form"
          :label-width="0"
          :model="formData">
          <PrimaryTable
            ref="compTableRef"
            class="dba-table mt-20"
            :data="formData.dataList"
            :max-height="tableMaxHeight"
            row-key="db_type">
            <TableColumn
              col-key="db_type_display"
              :title="t('组件类型')">
              <template #default="{ row }: { row: IRowData }">
                <div class="db-type">
                  <DbIcon
                    class="db-type-icon"
                    svg
                    :type="DBTypeInfos[row.db_type as DBTypes].icon" />
                  <span class="ml-4">{{ row.db_type_display }}</span>
                </div>
              </template>
            </TableColumn>
            <TableColumn col-key="users">
              <template #title>
                <div style="display: flex; align-items: center">
                  {{ t('默认 DBA') }}
                  <template v-if="isEdit">
                    <span class="required-star"> * </span>
                    <BatchEdit
                      field="user_edit"
                      :label="t('默认 DBA')"
                      :multiple="false"
                      @batch-edit="handleBatchEditColumn" />
                  </template>
                </div>
              </template>
              <template #default="{ row, rowIndex }: { row: IRowData, rowIndex: number }">
                <DbFormItem
                  v-if="isEdit"
                  error-display-type="tooltips"
                  :property="`dataList.${rowIndex}.user_edit`"
                  required>
                  <MemberSelector
                    v-model="row.user_edit"
                    :multiple="false"
                    @change="() => handleMemberChange(`dataList.${rowIndex}.user_edit`)" />
                </DbFormItem>
                <template v-else>
                  <MemberDisplay
                    v-if="row.users.length > 0"
                    :value="[row.users[0]]" />
                  <span v-else>--</span>
                </template>
              </template>
            </TableColumn>
          </PrimaryTable>
        </DbForm>
      </BkLoading>
    </div>
    <div v-if="isEdit">
      <BkButton
        v-bk-tooltips="{
          content: t('当前无变更，请先修改内容'),
          disabled: changedDataList.length > 0,
        }"
        class="w-88 mt-16"
        :disabled="changedDataList.length === 0"
        :loading="isUpdateAdminsLoading"
        theme="primary"
        @click="() => handleSave()">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88 ml-16"
        :disabled="isUpdateAdminsLoading"
        @click="() => handleCancel()">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DBAdminModel from '@services/model/db-admin/db-admin';
  import { getAdmins, updateGlobalAdmins } from '@services/source/dbadmin';

  import { DBAOperateTypes, DBTypeInfos, DBTypes } from '@common/const';

  import MemberSelector from '@components/db-member-selector/index.vue';

  import BatchEdit from '@views/staff-manage/common/BatchEdit.vue';
  import MemberDisplay from '@views/staff-manage/common/MemberDisplay.vue';

  import { getOffset, messageSuccess } from '@utils';

  type IRowData = { user_edit: string[] } & DBAdminModel;

  const { t } = useI18n();

  const rootRef = useTemplateRef('tableWrapper');
  const formRef = useTemplateRef('form');

  const tableMaxHeight = ref<number | 'auto'>('auto');
  const isEdit = ref(false);
  const formData = ref({
    dataList: [] as IRowData[],
  });

  const changedDataList = computed(() =>
    formData.value.dataList.filter((item) => !_.isEqual(item.users, item.user_edit)),
  );

  const { loading: isGetAdminsLoading, run: runGetAdmins } = useRequest(getAdmins, {
    manual: true,
    onSuccess(adminsData) {
      const adminsDataMap = Object.fromEntries(adminsData.data.map((item) => [item.db_type, item]));
      const defaultAdminData = Object.values(DBTypeInfos).map((item) => {
        if (adminsDataMap[item.id]) {
          return {
            ...adminsDataMap[item.id],
            user_edit: _.cloneDeep(adminsDataMap[item.id].users),
          };
        } else {
          return {
            bk_biz_id: 0,
            db_type: item.id,
            db_type_display: item.name,
            is_show: true,
            permission: {} as DBAdminModel['permission'],
            update_at: '',
            updater: '',
            user_edit: [] as string[],
            users: [] as string[],
          };
        }
      });
      formData.value.dataList = defaultAdminData;
    },
  });

  const { loading: isUpdateAdminsLoading, run: runUpdateAdmins } = useRequest(updateGlobalAdmins, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      isEdit.value = false;
      fetchData();
    },
  });

  const isLoading = computed(() => isGetAdminsLoading.value || isUpdateAdminsLoading.value);

  watch(isEdit, () => {
    setTableMaxHeight();
  });

  const fetchData = () => {
    runGetAdmins({
      bk_biz_id: 0,
    });
  };

  const handleMemberChange = (property: string) => {
    formRef.value?.validate(property);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    formData.value.dataList = formData.value.dataList.map((item) => ({
      ...item,
      [field]: value,
    }));
  };

  const handleEdit = () => {
    formData.value.dataList = formData.value.dataList.map((item) =>
      Object.assign(item, { user_edit: _.cloneDeep(item.users) }),
    );
    isEdit.value = true;
  };

  const handleSave = async () => {
    await formRef.value!.validate();

    const dbAdmins = changedDataList.value.map((item) => ({
      db_type: item.db_type,
      db_type_display: item.db_type_display,
      users: item.user_edit,
    }));
    const operates = changedDataList.value
      .map((item) => ({
        after: item.user_edit.join(','),
        before: item.users.join(','),
        bk_biz_id: 0,
        db_type: item.db_type as DBTypes,
        type: DBAOperateTypes.DEFAULT_DBA_CHANGE,
      }))
      .filter((item) => item.after !== item.before);

    runUpdateAdmins({
      bk_biz_id: 0,
      db_admins: dbAdmins,
      operates,
    });
  };

  const handleCancel = () => {
    isEdit.value = false;
  };

  const setTableMaxHeight = () => {
    nextTick(() => {
      tableMaxHeight.value =
        window.innerHeight - getOffset(rootRef.value as HTMLElement).top - (isEdit.value ? 48 : 0) - 20 - 20;
    });
  };

  onMounted(() => {
    fetchData();
    setTableMaxHeight();
  });
</script>

<style lang="less">
  .global-staff-manage-defalut-dba {
    padding: 16px 24px;

    .db-type {
      display: flex;
      align-items: center;

      .db-type-icon {
        font-size: 16px;
      }
    }

    .dba-table {
      .bk-form-item {
        &.is-error {
          .db-member-selector-copy {
            right: 24px;
          }
        }
      }

      .required-star {
        width: 12px;
        height: 12px;
        margin-left: 4px;
        color: #ea3636;
      }
    }
  }
</style>
