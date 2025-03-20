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
          show-select-all>
          <template #tag="{ selected: selectedTags }">
            <BkTag
              v-for="item in selectedTags"
              :key="item"
              closable
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
            v-for="item in alarmGroupList"
            :key="item.value"
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

  import { messageSuccess } from '@utils';

  interface Props {
    alarmGroupList: SelectItem<string>[];
    alarmGroupNameMap: Record<string, string>;
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
      title: t('批量替换'),
      tooltips: t('替换选中策略的告警组'),
    },
  ];

  const formData = reactive(initFormData());

  const { loading: isSubmitting, run: runBatchUpdateNotifyGroup } = useRequest(batchUpdateNotifyGroup, {
    manual: true,
    onSuccess() {
      messageSuccess(t('批量设置成功'));
      Object.assign(formData, initFormData());
      moduleValue.value = false;
      emits('suceess');
    },
  });

  const handleDeleteNotifyTargetItem = (id: number) => {
    const index = formData.notifyGroups.findIndex((item) => item === id);
    formData.notifyGroups.splice(index, 1);
  };

  const handleSubmit = () => {
    formRef.value!.validate().then(() => {
      const { notifyGroups: pageNotifyGroups, settingType } = formData;
      const isAppend = settingType === 'append';

      const paramNotifyGroups = props.selected.map((selectedItem) => {
        const groupIds = isAppend ? _.uniq([...selectedItem.notify_groups, ...pageNotifyGroups]) : pageNotifyGroups;
        return {
          groups: groupIds,
          policy_id: selectedItem.id,
        };
      });

      runBatchUpdateNotifyGroup({
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
