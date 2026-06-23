<template>
  <BkSideslider
    v-model:is-show="modelValue"
    quick-close
    :width="960"
    @hidden="handleHidden">
    <template #header>
      <div class="biz-unmanage-batch-remove-l2-dba-header">
        <div>{{ t('批量移除二线 DBA') }}</div>
        <div class="biz-bar ml-8"></div>
        <div class="biz-count ml-8">{{ t('已选 n 个业务', { n: selected.length }) }}</div>
      </div>
    </template>
    <template #default>
      <div class="biz-unmanage-batch-remove-l2-dba-content">
        <DbForm
          ref="form"
          form-type="vertical"
          :model="formData">
          <DbFormItem
            :label="t('待删除人员')"
            property="removeUsers"
            required>
            <MemberSelector v-model="formData.removeUsers" />
          </DbFormItem>
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

  import DiffTable from './common/DiffTableCommon.vue';

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
    removeUsers: [] as string[],
  });

  const formData = ref(getDefaultData());
  const diffData = ref<ComponentProps<typeof DiffTable>['data']>([]);

  const isFormEmpty = computed(() => {
    return formData.value.removeUsers.length === 0;
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
    const removeUsersMap = Object.fromEntries(formData.value.removeUsers.map((item) => [item, true]));

    return props.selected
      .filter((item) => item.users.length > 0)
      .flatMap((selectedItem) => {
        return [selectedItem.level2_dba].map((item) => ({
          after: item.filter((userItem) => !removeUsersMap[userItem]),
          before: item,
          bizId: selectedItem.bk_biz_id,
          bizName: selectedItem.name,
          isChanged: false,
          rowKey: random(),
          users: selectedItem.users,
        }));
      });
  };

  watch(
    [modelValue, formData],
    () => {
      if (modelValue.value) {
        const beforeList = getBeforeList();
        beforeList.forEach((item) => {
          Object.assign(item, {
            after: item.after,
            isChanged: !_.isEqual(item.before, item.after),
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
      const updateInfo = diffData.value
        .filter((rowItem) => rowItem.isChanged)
        .map((rowItem) => {
          return {
            bk_biz_id: Number(rowItem.bizId),
            db_admins: [{ db_type: props.dbType as DBTypes, users: rowItem.users.slice(0, 2).concat(rowItem.after) }],
          };
        });
      const params = {
        operates: changedData.value.map((item) => ({
          after: item.after.join(','),
          before: item.before.join(','),
          bk_biz_id: item.bizId,
          db_type: props.dbType as DBTypes,
          role: DBARoleTypes.LEVEL2_DBA,
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
  .biz-unmanage-batch-remove-l2-dba-header {
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

  .biz-unmanage-batch-remove-l2-dba-content {
    padding: 24px;

    .dba-box {
      display: flex;
      gap: 24px;

      .dba-item {
        flex: 1;
      }
    }
  }
</style>
