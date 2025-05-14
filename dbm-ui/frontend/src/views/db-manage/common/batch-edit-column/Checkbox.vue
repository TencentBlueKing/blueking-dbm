<template>
  <BkPopConfirm
    :is-show="isShow"
    trigger="manual"
    width="395"
    @cancel="() => (isShow = false)"
    @confirm="handleConfirmChange">
    <span>
      <slot />
    </span>
    <template #content>
      <div class="batch-edit-column-checkbox">
        <div class="main-title">{{ t('统一设置') }}{{ title }}</div>
        <div class="content-box">
          <span class="mr-8">{{ title }}</span>
          <BkCheckbox
            v-model="localValue"
            :disabled="disabled"
            :false-label="false"
            @change="handleChange" />
        </div>
      </div>
    </template>
  </BkPopConfirm>
</template>

<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  interface Props {
    disableFn?: (date?: Date | number) => boolean;
    title: string;
  }

  type Emits = (e: 'change', value: UnwrapRef<typeof localValue>) => void;

  const props = withDefaults(defineProps<Props>(), {
    disableFn: () => false,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>({
    default: false,
  });

  const { t } = useI18n();

  const localValue = ref(false);

  const disabled = computed(() => props.disableFn());

  const handleChange = (value: UnwrapRef<typeof localValue>) => {
    localValue.value = value;
  };

  const handleConfirmChange = () => {
    emits('change', localValue.value);
    isShow.value = false;
  };
</script>

<style lang="less">
  .batch-edit-column-checkbox {
    margin-bottom: 30px;

    & + .bk-pop-confirm-footer {
      button {
        width: 60px;
      }
    }

    .main-title {
      margin-bottom: 20px;
      font-size: 16px;
      color: #313238;
    }

    .content-box {
      display: flex;
      align-items: center;
    }
  }
</style>
