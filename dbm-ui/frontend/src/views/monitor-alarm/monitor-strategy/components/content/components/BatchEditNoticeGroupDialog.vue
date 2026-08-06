<template>
  <BkDialog
    v-model:is-show="moduleValue"
    class="batch-edit-notice-group-dialog"
    quick-close
    :width="500">
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
      <BkAlert
        v-if="isSkippedAlertShow"
        class="mb-8"
        theme="warning"
        :title="t('自动跳过 n 条策略（已包含本次选择的全部告警组），不受本次操作影响。', { n: skippedCount })" />
      <VoiceNotice
        v-if="isVoiceNoticeShow"
        v-model="formData.voiceNotice" />
      <div class="list-box mt-16">
        <div class="list-title">{{ t('本次将影响以下 n 条策略', { n: previewCount }) }}</div>
        <div
          v-if="formData.settingType === 'append' && formData.notifyGroups.length === 0"
          class="list-content">
          <div class="list-item">
            {{ t('请选择告警组后查看影响范围') }}
          </div>
        </div>
        <div
          v-else-if="formData.settingType === 'append' && changedSelected.length === 0"
          class="list-content">
          <div class="list-item">
            {{ t('本次没有需要追加的策略') }}
          </div>
        </div>
        <div
          v-else
          class="list-content">
          <div
            v-for="item in changedSelected"
            :key="item.id"
            class="list-item">
            {{ item.nameDisplay }}
          </div>
        </div>
      </div>
    </BkForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="changedSelected.length === 0"
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

  import { DBTypes } from '@common/const';

  import { getDbaLabel } from '@views/monitor-alarm/common/utils';

  import { messageSuccess } from '@utils';

  import VoiceNotice from '../../common/VoiceNotice.vue';

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
    voiceNotice: 'parallel',
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
    const groupItem = props.alarmGroupList.find((item) => item.label === getDbaLabel(props.dbType))!;
    return groupItem?.value;
  });

  const changedSelected = computed(() => {
    if (formData.settingType === 'append' && formData.notifyGroups.length > 0) {
      return props.selected.filter((selectedItem) => {
        const beforeValue = selectedItem.isInnerReal ? [bizDefaultGroupId.value] : selectedItem.notify_groups;
        const afterValue = _.uniq([
          ...(selectedItem.isInnerReal ? [bizDefaultGroupId.value] : []),
          ...selectedItem.notify_groups,
          ...formData.notifyGroups,
        ]);
        return !_.isEqual(_.sortBy(beforeValue), _.sortBy(afterValue));
      });
    }
    return props.selected;
  });
  const skippedCount = computed(() => props.selected.length - changedSelected.value.length);
  const isSkippedAlertShow = computed(() => formData.settingType === 'append' && skippedCount.value > 0);
  const isVoiceNoticeShow = computed(() => formData.settingType === 'replace' && formData.notifyGroups.length > 1);
  const previewCount = computed(() => {
    if (formData.settingType === 'replace') {
      return changedSelected.value.length;
    }
    if (formData.notifyGroups.length === 0) {
      return 0;
    }
    return changedSelected.value.length;
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

  watch(moduleValue, () => {
    if (moduleValue.value) {
      Object.assign(formData, initFormData());
    }
  });

  watch(
    () => formData.settingType,
    () => {
      if (formData.settingType === 'append') {
        formData.notifyGroups = [];
      } else {
        formData.notifyGroups = [bizDefaultGroupId.value];
        formData.voiceNotice = 'parallel';
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

      const paramNotifyGroups = changedSelected.value.map((selectedItem) => {
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

      const params = {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        notify_groups: paramNotifyGroups,
      };

      if (formData.settingType === 'replace') {
        Object.assign(params, {
          voice_notice: formData.notifyGroups.length > 1 ? formData.voiceNotice : 'parallel',
        });
      }

      runBatchUpdateNotifyGroup(params);
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

    .list-box {
      font-size: 12px;
      border: 1px solid #eaebf0;
      border-radius: 2px;

      .list-title {
        height: 32px;
        padding: 0 16px;
        line-height: 32px;
        color: #313238;
        background-color: #eaebf0;
      }

      .list-content {
        max-height: 200px;
        overflow: auto;

        .list-item {
          height: 32px;
          padding: 0 16px;
          line-height: 32px;

          &:nth-child(even) {
            background-color: #fafbfd;
          }
        }
      }
    }
  }
</style>
