<template>
  <BkSideslider
    v-model:is-show="modelValue"
    quick-close
    :width="960"
    @hidden="handleHidden">
    <template #header>
      <div class="biz-unmanage-batch-replace-header">
        <div>{{ t('批量替换业务 DBA') }}</div>
        <div class="biz-bar ml-8"></div>
        <div class="biz-count ml-8">{{ t('已选 n 个业务', { n: selected.length }) }}</div>
      </div>
    </template>
    <template #default>
      <div class="biz-unmanage-batch-replace-content">
        <DbForm
          ref="form"
          form-type="vertical"
          :model="formData">
          <DbFormItem
            :label="t('替换范围')"
            property="batchReplaceScope"
            required>
            <BkCheckboxGroup v-model="formData.batchReplaceScope">
              <BkCheckbox :label="DBARoleTypes.PRIMARY_DBA">{{ t('主 DBA') }}</BkCheckbox>
              <BkCheckbox :label="DBARoleTypes.BACKUP_DBA">{{ t('备 DBA') }}</BkCheckbox>
              <BkCheckbox :label="DBARoleTypes.LEVEL2_DBA">{{ t('二线 DBA') }}</BkCheckbox>
            </BkCheckboxGroup>
          </DbFormItem>
          <div class="dba-box">
            <DbFormItem
              class="dba-item"
              :label="t('待替换人员')"
              property="before"
              required>
              <MemberSelector
                v-model="formData.before"
                :multiple="false" />
            </DbFormItem>
            <div class="replace-circle">
              <DbIcon
                class="arrow-right"
                type="arrow-right" />
            </div>
            <DbFormItem
              class="dba-item"
              :label="t('替换成')"
              property="after"
              required>
              <MemberSelector
                v-model="formData.after"
                :multiple="false" />
            </DbFormItem>
          </div>
        </DbForm>
        <DiffTable
          ref="diffTable"
          :data="diffData"
          :is-form-empty="isFormEmpty"
          :user-data-map="userDataMap" />
      </div>
    </template>
    <template #footer>
      <BkButton
        :disabled="changedData.length === 0"
        :loading="loading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确认') }}
      </BkButton>
      <BkButton
        class="ml-8"
        :disabled="loading"
        @click="modelValue = false">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { batchUpsertAdmins } from '@services/source/dbadmin';

  import { DBAOperateTypes, DBARoleTypes, DBTypes } from '@common/const';

  import MemberSelector from '@components/db-member-selector/index.vue';

  import { messageSuccess, random } from '@utils';

  import BizDbaModel from '../bizDba';

  import DiffTable from './common/DiffTableWithRole.vue';

  export interface Props {
    dbType: string;
    selected: BizDbaModel[];
    userDataMap: Record<string, string>;
  }

  export type Emits = (e: 'success') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<boolean>({ required: true });

  const { t } = useI18n();

  const formRef = useTemplateRef('form');

  const getDefaultData = () => ({
    after: [] as string[],
    batchReplaceScope: [DBARoleTypes.PRIMARY_DBA, DBARoleTypes.BACKUP_DBA, DBARoleTypes.LEVEL2_DBA],
    before: [] as string[],
  });

  const formData = ref(getDefaultData());
  const diffData = ref<ComponentProps<typeof DiffTable>['data']>([]);

  const isFormEmpty = computed(() => {
    return (
      formData.value.batchReplaceScope.length === 0 ||
      formData.value.before.length === 0 ||
      formData.value.after.length === 0
    );
  });
  const changedData = computed(() => diffData.value.filter((item) => item.isChanged));

  const { loading, run: runBatchUpsertAdmins } = useRequest(batchUpsertAdmins, {
    manual: true,
    onSuccess() {
      messageSuccess(t('操作成功'));
      formData.value = getDefaultData();
      modelValue.value = false;
      emits('success');
    },
  });

  const getBeforeList = () => {
    const roleMap = {
      0: DBARoleTypes.PRIMARY_DBA,
      1: DBARoleTypes.BACKUP_DBA,
      2: DBARoleTypes.LEVEL2_DBA,
    };
    return props.selected
      .filter((item) => item.users.length > 0)
      .flatMap((selectedItem) => {
        return [
          selectedItem.primary_dba ? [selectedItem.primary_dba] : [],
          selectedItem.standby_dba ? [selectedItem.standby_dba] : [],
          selectedItem.level2_dba,
        ].map((item, index) => ({
          after: [] as string[],
          before: item,
          bizId: selectedItem.bk_biz_id,
          bizName: selectedItem.name,
          isChanged: false,
          role: roleMap[index as keyof typeof roleMap],
          rowKey: random(),
        }));
      });
  };

  watch(
    [modelValue, formData],
    () => {
      if (modelValue.value) {
        const beforeList = getBeforeList();
        // const roleMap = {
        //   [DBARoleTypes.BACKUP_DBA]: formData.value.batchReplaceScope.includes(DBARoleTypes.BACKUP_DBA) ? formData.value.after : [],
        //   [DBARoleTypes.LEVEL2_DBA]: formData.value.batchReplaceScope.includes(DBARoleTypes.LEVEL2_DBA) ? formData.value.after : [],
        //   [DBARoleTypes.PRIMARY_DBA]: formData.value.batchReplaceScope.includes(DBARoleTypes.PRIMARY_DBA) ? formData.value.after : [],
        // };
        beforeList.forEach((item) => {
          let afterValue = item.before;
          if (
            formData.value.batchReplaceScope.includes(item.role) &&
            formData.value.before.length > 0 &&
            formData.value.after.length > 0
          ) {
            afterValue = _.uniq(
              item.before.map((beforeItem) => {
                if (beforeItem === formData.value.before[0]) {
                  return formData.value.after[0];
                }
                return beforeItem;
              }),
            );
          }

          Object.assign(item, {
            after: afterValue,
            isChanged: !_.isEqual(item.before, afterValue),
          });
        });

        diffData.value = beforeList;
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleConfirm = () => {
    formRef.value!.validate().then(() => {
      const groupInfo = _.groupBy(diffData.value, (item) => item.bizId);
      const updateInfo = Object.entries(groupInfo)
        .filter(([_bizId, rows]) => rows.some((rowItem) => rowItem.isChanged))
        .map(([bizId, rows]) => {
          let primaryDBA: string[] = [];
          let standbyDBA: string[] = [];
          let level2DBA: string[] = [];

          rows.forEach((rowItem) => {
            if (rowItem.role === DBARoleTypes.PRIMARY_DBA) {
              primaryDBA = primaryDBA.concat(rowItem.isChanged ? rowItem.after : rowItem.before);
            } else if (rowItem.role === DBARoleTypes.BACKUP_DBA) {
              standbyDBA = standbyDBA.concat(rowItem.isChanged ? rowItem.after : rowItem.before);
            } else if (rowItem.role === DBARoleTypes.LEVEL2_DBA) {
              level2DBA = level2DBA.concat(rowItem.isChanged ? rowItem.after : rowItem.before);
            }
          });

          return {
            bk_biz_id: Number(bizId),
            db_admins: [
              {
                db_type: props.dbType as DBTypes,
                users: [...primaryDBA, ...standbyDBA, ...level2DBA],
              },
            ],
          };
        });
      const params = {
        operates: changedData.value.map((item) => ({
          after: item.after.join(','),
          before: item.before.join(','),
          bk_biz_id: item.bizId,
          db_type: props.dbType as DBTypes,
          role: item.role,
          type: DBAOperateTypes.DBA_CHANGE,
        })),
        update_info: updateInfo,
      };
      runBatchUpsertAdmins(params);
    });
  };

  const handleHidden = () => {
    formData.value = getDefaultData();
  };
</script>

<style lang="less">
  .biz-unmanage-batch-replace-header {
    display: flex;
    align-items: center;

    .biz-bar {
      width: 1px;
      height: 14px;
      background-color: #dcdee5;
    }

    .biz-count {
      font-size: 14px;
      color: #979ba5;
    }
  }

  .biz-unmanage-batch-replace-content {
    padding: 24px;

    .dba-box {
      display: flex;
      gap: 24px;
      align-items: center;

      .bk-form-item {
        margin-bottom: 24px;
      }

      .dba-item {
        flex: 1;
      }

      .replace-circle {
        display: flex;
        width: 32px;
        height: 32px;
        justify-content: center;
        align-items: center;
        color: #979ba5;
        background: #f5f7fa;
        border-radius: 999px;

        .arrow-right {
          font-size: 16px;
        }
      }
    }
  }
</style>
