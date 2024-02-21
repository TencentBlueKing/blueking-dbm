<template>
  <BkPopover
    v-model:is-show="stateShow"
    :boundary="body"
    class="batch-edit"
    theme="light"
    trigger="manual"
    :width="540">
    <i
      class="db-icon-bulk-edit batch-edit-trigger"
      @click="() => stateShow = true" />

    <template #content>
      <div class="batch-edit-content">
        <p class="batch-edit-header">
          {{ t('快捷编辑') }}
          <span>{{ t('通过换行分隔_快速批量编辑多个域名') }}</span>
        </p>
        <div
          class="batch-edit-domain"
          :style="{ '--offset': `${stateOffsetWidth}px` }">
          <p class="batch-edit-domain-name">
            <span ref="moduleNameRef">
              {{ moduleName }}db.
            </span>
            <span class="batch-edit-domain-underline" />
            .{{ appName }}.db
          </p>
          <BkInput
            v-model="stateValue"
            class="batch-edit-domain-input"
            :placeholder="t('以小写英文字母开头_且只能包含小写英文字母_数字_连字符_多个换行分隔')"
            :rows="textareaRows"
            type="textarea" />
          <p
            v-if="validateShow"
            class="batch-edit-domain-error">
            {{ validateErrorTxt }}
          </p>
        </div>
        <div class="batch-edit-footer">
          <BkButton
            class="mr-8"
            size="small"
            theme="primary"
            @click="handleConfirm">
            {{ t('确定') }}
          </BkButton>
          <BkButton
            size="small"
            @click="handleCancel">
            {{ t('取消') }}
          </BkButton>
        </div>
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { nameRegx } from '@common/regex';

  interface Props {
    moduleName?: string,
    appName?: string,
  }

  interface Emits {
    (e: 'change', value: string[]): void
  }

  withDefaults(defineProps<Props>(), {
    moduleName: '',
    appName: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const errorTxt = {
    rule: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
    repeat: t('输入域名重复'),
    maxlength: t('最大长度为m', { m: 63 }),
  };


  /**
   * 获取输入框 arrow 偏移量
   */
  const moduleNameRef = ref<HTMLSpanElement>();

  const stateShow = ref(false);
  const stateValue = ref('');
  const stateOffsetWidth = ref(0);
  const validateShow = ref(false);
  const validateErrorTxt = ref('');
  const validateResult = ref();

  const { body } = document;

  const textareaRows = computed(() => {
    const rows = stateValue.value.split('\n').length;
    if (rows <= 5) {
      return 5;
    }
    return rows > 10 ? 10 : rows;
  });

  watch(stateShow, (show) => {
    nextTick(() => {
      if (moduleNameRef.value) {
        stateOffsetWidth.value = moduleNameRef.value.offsetWidth + 22;
      }
    });
    if (!show) {
      stateValue.value = '';
      validateShow.value = false;
    }
  });

  /**
   * validate batch edit value
   */
  const handleValidate = () => {
    const newDomains = stateValue.value.split('\n');
    // 最大长度
    const maxlengthRes = newDomains.every(key => key.length <= 63);
    if (!maxlengthRes) {
      validateErrorTxt.value = errorTxt.maxlength;
      validateShow.value = true;
      return false;
    }

    const validate = newDomains.every(key => nameRegx.test(key));
    if (!validate) {
      validateErrorTxt.value = errorTxt.rule;
      validateShow.value = !validate;
      return validate;
    }
    // 校验名称是否重复
    const uniqDomains = _.uniq(newDomains);
    const hasRepeat = newDomains.length !== uniqDomains.length;
    validateErrorTxt.value = errorTxt.repeat;
    validateShow.value = hasRepeat;
    return !hasRepeat;
  };

  watch(stateValue, (value) => {
    if (value) {
      validateResult.value = handleValidate();
    }
  });

  /**
   * confirm batch edit
   */
  const handleConfirm = () => {
    if (!validateResult.value) {
      return;
    }
    if (validateShow.value) {
      return;
    }

    const newDomains = stateValue.value.split('\n');
    emits('change', newDomains);
    handleCancel();
  };

  /**
   * close popover
   */
  const handleCancel = () => {
    stateShow.value = false;
  };
</script>

<style lang="less" scoped>
.batch-edit {
  .batch-edit-trigger {
    margin-left: 5px;
    color: @primary-color;
    cursor: pointer;
  }

  .batch-edit-content {
    padding: 9px 2px;
  }

  .batch-edit-header {
    padding-bottom: 16px;
    font-size: @font-size-large;
    color: @title-color;

    span {
      font-size: @font-size-mini;
      color: @default-color;
    }
  }

  .batch-edit-domain {
    position: relative;
    color: @default-color;

    .batch-edit-domain-name {
      word-wrap: break-word;
    }

    .batch-edit-domain-underline {
      position: relative;
      display: inline-block;
      width: 54px;
      height: 1px;
      margin: 0 2px;
      color: @default-color;
      background-color: #c4c6cc;

      &::after {
        position: absolute;
        top: -4px;
        left: 50%;
        z-index: 1;
        width: 6px;
        height: 6px;
        background-color: white;
        border: 1px solid transparent;
        border-bottom-color: #c4c6cc;
        border-left-color: #c4c6cc;
        content: '';
        transform: translateX(-50%) rotate(-45deg);
      }
    }

    .batch-edit-domain-input {
      position: relative;
      margin: 12px 0 16px;

      &::before {
        position: absolute;
        top: -4px;
        left: var(--offset);
        width: 6px;
        height: 6px;
        background-color: @white-color;
        border: 1px solid transparent;
        border-top-color: @border-light-gray;
        border-left-color: @border-light-gray;
        content: "";
        transform: rotateZ(45deg);
      }

      .batch-edit.is-focused {
        &::before {
          border-top-color: @border-primary;
          border-left-color: @border-primary;
        }
      }
    }

    .batch-edit-domain-error {
      position: absolute;
      bottom: -4px;
      left: 0;
      font-size: @font-size-mini;
      color: @danger-color;
    }
  }

  .batch-edit-footer {
    text-align: right;

    .bk-button {
      min-width: 60px;
      font-size: 12px;
    }
  }
}
</style>
