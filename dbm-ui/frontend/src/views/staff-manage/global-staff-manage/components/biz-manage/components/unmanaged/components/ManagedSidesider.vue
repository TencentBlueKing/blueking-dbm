<template>
  <BkSideslider
    v-model:is-show="modelValue"
    quick-close
    :width="960">
    <template #header>
      <div class="biz-unmanage-sideslider-header">
        <div>{{ t('纳管业务') }}</div>
        <div class="biz-bar ml-8"></div>
        <div class="biz-name ml-8">{{ props.data.name }}</div>
      </div>
    </template>
    <template #default>
      <BkLoading
        :loading="isGetAdminsLoading"
        style="height: 100%">
        <DbForm
          ref="form"
          class="biz-unmanage-sideslider"
          form-type="vertical"
          :label-width="100"
          :model="formData"
          :scroll-align-to-top="false">
          <DbFormItem
            :label="t('业务代号')"
            property="bizCode"
            required
            :rules="bizCodeRules">
            <div class="biz-code-item">
              <BkInput
                v-model="formData.bizCode"
                :disabled="bizCodeDisabled"
                :placeholder="t('以小写字母开头，仅包含小写字母、数字、连字符（-），长度 2~32')" />
              <!-- <div
                v-if="bizCodeDisabled"
                class="biz-code-hint">
                {{ t('已从 CMDB 获取，不可修改') }}
              </div> -->
            </div>
          </DbFormItem>
          <div class="dba-label">{{ t('配置业务 DBA') }}</div>
          <BkAlert class="mt-8">
            <template #title>
              <div>
                {{ t('为各 DB 组件配置 DBA。未配置的组件沿用该组件默认 DBA。主、备 DBA 必须同时填写。') }}
              </div>
              <!-- <div>
                  <span class="alert-bord">{{ t('注意：') }}</span>
                  {{ t('单个组件如填写了任一角色，则主 DBA、备 DBA 必填，二线 DBA 可选。') }}
                </div> -->
            </template>
          </BkAlert>
          <div ref="tableWrapper">
            <PrimaryTable
              class="mt-16"
              :data="formData.tableData"
              :max-height="tableMaxHeight"
              :outer-border="false"
              row-key="dbType">
              <TableColumn
                col-key="dbTypeName"
                :title="t('组件类型')"
                width="120" />
              <TableColumn
                col-key="mainDba"
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
                      class="ml-4"
                      :disabled="!hasEditRow"
                      field="primaryDBA"
                      :label="t('主 DBA')"
                      :multiple="false"
                      @batch-edit="handleBatchEdit" />
                  </div>
                </template>
                <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
                  <DbFormItem
                    v-if="row.isEdit"
                    class="primary-dba-form-item"
                    error-display-type="tooltips"
                    :property="`tableData.${rowIndex}.primaryDBA`"
                    :rules="[
                      {
                        required: true,
                        message: t('主备必须成对填写'),
                        validator: (value: string[]) => value.length > 0,
                      },
                    ]">
                    <div class="member-selector-wrapper">
                      <MemberSelector
                        v-model="row.primaryDBA"
                        class="member-selector"
                        :multiple="false"
                        @change="() => handleMemberChange(`tableData.${rowIndex}.primaryDBA`)" />
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
                      v-if="isPrimaryAndStanbySame(row)"
                      class="member-selector-tip">
                      <DbIcon
                        class="mr-4"
                        type="attention" />
                      <span>{{ t('主备 DBA 为同一人') }}</span>
                    </div>
                  </DbFormItem>
                  <BkButton
                    v-else
                    text
                    theme="primary"
                    @click="handleEditRow(row, rowIndex)">
                    {{ t('添加') }}
                  </BkButton>
                </template>
              </TableColumn>
              <TableColumn
                col-key="backupDba"
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
                      class="ml-4"
                      :disabled="!hasEditRow"
                      field="standbyDBA"
                      :label="t('备 DBA')"
                      :multiple="false"
                      @batch-edit="handleBatchEdit" />
                  </div>
                </template>
                <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
                  <DbFormItem
                    v-if="row.isEdit"
                    error-display-type="tooltips"
                    :property="`tableData.${rowIndex}.standbyDBA`"
                    :rules="[
                      {
                        required: true,
                        message: t('主备必须成对填写'),
                        validator: (value: string[]) => value.length > 0,
                      },
                    ]">
                    <MemberSelector
                      v-model="row.standbyDBA"
                      :multiple="false"
                      :property="`tableData.${rowIndex}.standbyDBA`"
                      @change="() => handleMemberChange(`tableData.${rowIndex}.standbyDBA`)" />
                    <div
                      v-if="isPrimaryAndStanbySame(row)"
                      class="member-selector-tip"></div>
                  </DbFormItem>
                </template>
              </TableColumn>
              <TableColumn
                col-key="secondDbaList"
                min-width="200">
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
                      class="ml-4"
                      :disabled="!hasEditRow"
                      field="level2DBA"
                      :label="t('二线 DBA')"
                      @batch-edit="handleBatchEdit" />
                  </div>
                </template>
                <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
                  <DbFormItem v-if="row.isEdit">
                    <div class="member-selector-wrapper">
                      <MemberSelector
                        v-model="row.level2DBA"
                        class="member-selector"
                        fast-clear />
                      <BkButton
                        v-bk-tooltips="t('删除')"
                        class="ml-8"
                        text
                        @click="handleDeleteRow(row, rowIndex)">
                        <DbIcon
                          class="delete-icon"
                          type="delete" />
                      </BkButton>
                      <div
                        v-if="isPrimaryAndStanbySame(row)"
                        class="member-selector-tip" />
                    </div>
                  </DbFormItem>
                </template>
              </TableColumn>
            </PrimaryTable>
          </div>
        </DbForm>
      </BkLoading>
    </template>
    <template #footer>
      <BkButton
        :loading="isManageBizLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确认纳管') }}
      </BkButton>
      <BkButton
        class="ml-16"
        :disabled="isManageBizLoading"
        @click="modelValue = false">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAdmins, manageBiz } from '@services/source/dbadmin';
  import type { BizItem } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import MemberSelector from '@components/db-member-selector/index.vue';

  import BatchEdit from '@views/staff-manage/common/BatchEdit.vue';

  import { bizCodeRegx } from '@/common/regex';
  import { getOffset, messageSuccess } from '@/utils';

  interface Props {
    data: BizItem;
  }

  type Emits = (e: 'success') => void;

  interface IRowData {
    dbType: DBTypes;
    dbTypeName: string;
    isEdit: boolean;
    level2DBA: string[];
    primaryDBA: string[];
    standbyDBA: string[];
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<boolean>({ required: true });

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const codePlaceholder = t('以小写英文字母开头_且只能包含英文字母_数字_连字符');
  const bizCodeRules = [
    {
      message: codePlaceholder,
      trigger: 'change',
      validator: (val: string) => {
        if (bizCodeDisabled.value) {
          return true;
        }
        return bizCodeRegx.test(val) && val.length >= 2 && val.length <= 32;
      },
    },
    {
      message: t('业务code不允许重复'),
      trigger: 'blur',
      validator: (val: string) => {
        if (bizCodeDisabled.value) {
          return true;
        }
        return !bizs.find((item) => item.english_name === val);
      },
    },
  ];

  const rootRef = useTemplateRef('tableWrapper');
  const formRef = useTemplateRef('form');
  const bizCodeDisabled = ref(false);
  const formData = ref({
    bizCode: '',
    tableData: [] as IRowData[],
  });
  const tableMaxHeight = ref<number | 'auto'>('auto');

  const hasEditRow = computed(() => formData.value.tableData.some((item) => item.isEdit));

  const { loading: isGetAdminsLoading, run: runGetAdmins } = useRequest(getAdmins, {
    manual: true,
    onSuccess(adminData) {
      const usersMap = Object.fromEntries(adminData.data.map((item) => [item.db_type, item.users]));
      formData.value.tableData = Object.keys(DBTypeInfos).map((dbType) => {
        const [primaryDBA, standbyDBA, ...level2DBA] = usersMap[dbType] || [];
        return {
          dbType: dbType as DBTypes,
          dbTypeName: DBTypeInfos[dbType as DBTypes].name,
          isEdit: false,
          level2DBA: level2DBA || [],
          primaryDBA: primaryDBA ? [primaryDBA] : [],
          standbyDBA: standbyDBA ? [standbyDBA] : [],
        };
      });
    },
  });

  const { loading: isManageBizLoading, run: runManageBiz } = useRequest(manageBiz, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      modelValue.value = false;
      emits('success');
    },
  });

  watch(modelValue, () => {
    if (modelValue.value) {
      formRef.value!.clearValidate();
    }
  });

  watch(
    () => props.data,
    () => {
      formData.value.bizCode = props.data.english_name;
      bizCodeDisabled.value = !!props.data.english_name;
      runGetAdmins({
        bk_biz_id: props.data.bk_biz_id,
      });
    },
    {
      immediate: true,
    },
  );

  const handleSwitchPrimaryAndStandby = (row: IRowData, rowIndex: number) => {
    const { primaryDBA, standbyDBA } = row;
    formData.value.tableData[rowIndex] = Object.assign(row, {
      primaryDBA: standbyDBA,
      standbyDBA: primaryDBA,
    });
  };

  const isPrimaryAndStanbySame = (row: IRowData) => {
    return row.primaryDBA.length > 0 && row.standbyDBA.length > 0 && row.primaryDBA[0] === row.standbyDBA[0];
  };

  const handleMemberChange = (property: string) => {
    formRef.value?.validate(property);
  };

  const handleEditRow = (row: IRowData, rowIndex: number) => {
    formData.value.tableData[rowIndex] = Object.assign(row, {
      isEdit: true,
    });
  };

  const handleDeleteRow = (row: IRowData, rowIndex: number) => {
    formData.value.tableData[rowIndex] = Object.assign(row, {
      isEdit: false,
    });
  };

  const handleBatchEdit = (value: any, field: string) => {
    formData.value.tableData.forEach((item) => {
      if (item.isEdit) {
        Object.assign(item, {
          [field]: value,
        });
      }
    });
  };

  const handleConfirm = async () => {
    await formRef.value!.validate();
    runManageBiz({
      app_code: bizCodeDisabled.value ? undefined : formData.value.bizCode,
      bk_biz_id: props.data.bk_biz_id,
      db_admins: formData.value.tableData
        .filter((item) => item.isEdit && [...item.primaryDBA, ...item.standbyDBA, ...item.level2DBA].length > 0)
        .map((item) => {
          return {
            db_type: item.dbType,
            users: [...item.primaryDBA, ...item.standbyDBA, ...item.level2DBA],
          };
        }),
    });
  };

  const setTableMaxHeight = () => {
    nextTick(() => {
      tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 72;
    });
  };

  onMounted(() => {
    setTableMaxHeight();
  });
</script>

<style lang="less">
  .biz-unmanage-sideslider-header {
    display: flex;
    align-items: center;

    .biz-bar {
      width: 1px;
      height: 14px;
      background-color: #dcdee5;
    }

    .biz-name {
      font-size: 14px;
      color: #979ba5;
    }
  }

  .biz-unmanage-sideslider {
    padding: 24px;

    // .biz-code-item {
    // }

    .dba-label {
      font-weight: bolder;
      color: #313238;
    }

    .alert-bord {
      font-weight: bolder;
    }

    .primary-dba-form-item {
      .bk-form-error-tips {
        right: 44px;
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

      .delete-icon {
        font-size: 14px;
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
</style>
