<template>
  <BkButton
    class="ml-16"
    text
    theme="primary"
    @click="() => (isShow = true)">
    {{ t('调整策略') }}
  </BkButton>
  <BkDialog
    v-model:is-show="isShow"
    class="to-alarm-policy-dialog"
    quick-close
    :title="t('调整告警策略')"
    :width="500">
    <div class="text-box">
      <BkAlert
        class="mt-8"
        theme="info"
        :title="t('当前告警由策略「name」触发，对业务下全部对象生效。如需调整，可选择：', { name: props.name })" />
      <BkRadioGroup
        v-model="type"
        class="radio-group">
        <template v-if="isChild">
          <BkRadio
            class="radio-group-item"
            :label="Type.CHILD_EDIT">
            {{ t('编辑子策略') }}
          </BkRadio>
        </template>
        <template v-else>
          <BkRadio
            class="radio-group-item"
            :label="Type.PARENT_EDIT">
            {{ t('') }}
            <span>{{ t('编辑策略') }}</span>
            <span class="item-desc">（{{ t('全局调整，对所有对象生效') }}）</span>
          </BkRadio>
          <BkRadio
            class="radio-group-item"
            :label="Type.PARENT_NEW">
            <span>{{ t('去新增子策略') }}</span>
            <span class="item-desc">（{{ t('针对特定对象补充精细化规则') }}）</span>
          </BkRadio>
        </template>
      </BkRadioGroup>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import AlarmEventModel from '@services/model/monitor/alarm-event';

  import { MonitorTargetLevel } from '@common/const';

  interface Props {
    data: AlarmEventModel['dbm_policy'];
    name: string;
  }
  type Emits = (e: 'confirm', editType: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  enum Type {
    CHILD_EDIT = 'child_edit',
    PARENT_EDIT = 'parent_edit',
    PARENT_NEW = 'parent_new',
  }

  const type = ref<Type>(Type.PARENT_EDIT);
  const isShow = ref(false);

  const isChild = computed(
    () =>
      props.data.bk_biz_id !== 0 &&
      ![MonitorTargetLevel.BIZ, MonitorTargetLevel.PLATFORM].includes(props.data.target_level),
  );

  watch(
    isChild,
    () => {
      type.value = isChild.value ? Type.CHILD_EDIT : Type.PARENT_EDIT;
    },
    {
      immediate: true,
    },
  );

  const handleConfirm = () => {
    emits('confirm', type.value as string);
    isShow.value = false;
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>

<style lang="less">
  .to-alarm-policy-dialog {
    .text-box {
      .radio-group {
        flex-direction: column;
        margin-top: 4px;

        .radio-group-item {
          margin-top: 12px;
          margin-left: 0 !important;

          .bk-radio-label {
            font-size: 12px;
          }

          .item-desc {
            color: #979ba5;
          }
        }
      }
    }
  }
</style>
