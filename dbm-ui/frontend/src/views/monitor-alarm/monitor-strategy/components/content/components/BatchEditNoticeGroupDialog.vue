<template>
  <BkDialog
    v-model:is-show="moduleValue"
    class="batch-edit-notice-group-dialog"
    quick-close>
    <template #header>
      <span>{{ t('批量设置告警组') }}</span>
      <span class="sub-title">{{ t('已选n个策略', { n: selected.length }) }}</span>
    </template>
    <BkForm
      ref="form"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('设置类型')"
        property="settingType"
        required>
        <BkRadioGroup
          v-model="formData.settingType"
          type="card">
          <BkRadioButton
            v-for="item in settingTypes"
            :key="item.label"
            :label="item.label">
            <span
              v-bk-tooltips="item.tooltips"
              class="radio-title">
              {{ item.title }}
            </span>
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('告警组')"
        property="notifyGroups"
        required>
        <BkSelect
          v-model="formData.notifyGroups"
          class="notify-select"
          filterable
          multiple
          multiple-mode="tag"
          :show-all="false"
          show-select-all
          @change="handleChange"
          @clear="handleClear">
          <template #tag="{ selected: selectedTags }">
            <BkTag
              v-for="item in selectedTags"
              :key="item.value"
              v-bk-tooltips="{
                content: t('默认组件 DBA，不可删除'),
                disabled: item.value !== bizDefaultGroupId,
              }"
              :closable="formData.settingType === 'replace' && item.value === bizDefaultGroupId ? false : true"
              @close="() => handleDeleteNotifyTargetItem(item.value)">
              <template #icon>
                <DbIcon
                  class="alarm-icon"
                  type="yonghuzu" />
              </template>
              {{ alarmGroupNameMap[item.value] }}
            </BkTag>
          </template>
          <BkOption
            v-for="item in alarmGroupSelectList"
            :key="item.value"
            :disabled="item.value === bizDefaultGroupId"
            :label="item.label"
            :value="item.value" />
        </BkSelect>
      </BkFormItem>
    </BkForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        :disabled="isSubmitting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { batchUpdateNotifyGroup } from '@services/source/monitor';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  interface Props {
    alarmGroupList: SelectItem<number>[];
    alarmGroupNameMap: Record<string, string>;
    dbType: DBTypes;
    selected: MonitorPolicyModel[];
  }

  type Emits = (e: 'suceess') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const moduleValue = defineModel<boolean>();

  const { t } = useI18n();

  const formRef = useTemplateRef('form');

  const initFormData = () => ({
    notifyGroups: [] as number[],
    settingType: 'append',
  });

  const settingTypes = [
    {
      label: 'append',
      title: t('批量追加'),
      tooltips: t('为选中策略追加新的告警组'),
    },
    {
      label: 'replace',
      title: t('批量覆盖'),
      tooltips: t('覆盖选中策略的告警组配置'),
    },
  ];

  const formData = reactive(initFormData());

  const bizDefaultGroupId = computed(() => {
    const groupItem = props.alarmGroupList.find((item) => item.label === `${DBTypeInfos[props.dbType].name}_DBA`)!;
    return groupItem?.value;
  });

  const alarmGroupSelectList = computed(() => {
    if (formData.settingType === 'append') {
      return props.alarmGroupList.filter((item) => item.value !== bizDefaultGroupId.value);
    }
    return props.alarmGroupList;
  });

  const { loading: isSubmitting, run: runBatchUpdateNotifyGroup } = useRequest(batchUpdateNotifyGroup, {
    manual: true,
    onSuccess() {
      messageSuccess(t('批量设置成功'));
      Object.assign(formData, initFormData());
      moduleValue.value = false;
      emits('suceess');
    },
  });

  watch(
    () => formData.settingType,
    () => {
      if (formData.settingType === 'append') {
        formData.notifyGroups = formData.notifyGroups.filter((item) => item !== bizDefaultGroupId.value);
      } else {
        const groups = formData.notifyGroups;
        groups.splice(0, 1, bizDefaultGroupId.value);
        formData.notifyGroups = groups;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClear = () => {
    if (formData.settingType === 'replace') {
      formData.notifyGroups = [bizDefaultGroupId.value];
    }
  };

  const handleChange = () => {
    if (formData.settingType === 'replace' && formData.notifyGroups.every((item) => item !== bizDefaultGroupId.value)) {
      const groups = formData.notifyGroups;
      groups.splice(0, 0, bizDefaultGroupId.value);
      formData.notifyGroups = groups;
    }
  };

  const handleDeleteNotifyTargetItem = (id: number) => {
    const index = formData.notifyGroups.findIndex((item) => item === id);
    formData.notifyGroups.splice(index, 1);
  };

  const handleSubmit = () => {
    formRef.value!.validate().then(() => {
      const { notifyGroups: pageNotifyGroups, settingType } = formData;
      const isAppend = settingType === 'append';

      const paramNotifyGroups = props.selected.map((selectedItem) => {
        let groupIds = pageNotifyGroups;
        if (isAppend) {
          groupIds = _.uniq([
            ...(selectedItem.isInnerReal ? [bizDefaultGroupId.value] : []),
            ...selectedItem.notify_groups,
            ...pageNotifyGroups,
          ]);
        }

        return {
          groups: groupIds,
          policy_id: selectedItem.id,
        };
      });

      runBatchUpdateNotifyGroup({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        notify_groups: paramNotifyGroups,
      });
    });
  };

  const handleCancel = () => {
    moduleValue.value = false;
  };
</script>

<style lang="less">
  .batch-edit-notice-group-dialog {
    .sub-title {
      padding-left: 8px;
      margin-left: 8px;
      font-size: 14px;
      color: #979ba5;
      border-left: 1px solid #dcdee5;
    }

    .radio-title {
      font-size: 14px;
      border-bottom: 1px dashed;
    }
  }
</style>
