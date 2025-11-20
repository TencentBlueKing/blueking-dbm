<template>
  <div class="key-value-pair-main">
    <div class="key-input-wraper">
      <BkInput
        v-model="pairInfo.key"
        class="key-input"
        :class="{ 'is-not-valid': !isKeyVerifyPass }"
        @change="checkInputKey" />
      <DbIcon
        v-if="!isKeyVerifyPass"
        v-bk-tooltips="keyVerifyTip"
        class="error-icon"
        type="exclamation-fill" />
    </div>
    <TagValueInput
      ref="valueInputRef"
      v-model="pairInfo.value"
      class="value-input-wraper" />
    <div class="operation-main">
      <DbIcon
        class="add-icon"
        type="plus-fill"
        @click="handleAdd" />
      <DbIcon
        class="delete-icon ml-10"
        type="minus-fill"
        @click="handleDelete" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { tagKeyRegex } from '@common/regex';

  import TagValueInput from './components/TagValueInput.vue';

  interface Props {
    data: typeof pairInfo.value;
    existedKeys: Set<string>;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'delete'): void;
  }

  interface Exposes {
    getValue: () => Record<string, string[]> | null;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const valueInputRef = ref<InstanceType<typeof TagValueInput>>();
  const pairInfo = ref({
    key: '',
    value: [] as string[],
  });
  const isKeyVerifyPass = ref(true);
  const keyVerifyTip = ref(t('必填'));

  watch(
    () => props.data,
    () => {
      if (props.data.key) {
        pairInfo.value.key = props.data.key;
        pairInfo.value.value = props.data.value;
        keyVerifyTip.value = '';
      }
    },
    { immediate: true },
  );

  watch(keyVerifyTip, () => {
    isKeyVerifyPass.value = !keyVerifyTip.value;
  });

  const checkInputKey = (key: string) => {
    if (!key) {
      keyVerifyTip.value = t('必填');
      return;
    }

    if (props.existedKeys.has(key)) {
      keyVerifyTip.value = t('标签键已存在');
      return;
    }

    if (!tagKeyRegex.test(key)) {
      keyVerifyTip.value = t('标签键为1-50个字符，支持英文字母、数字或汉字，中划线(-)，下划线(_)，点(.)');
      return;
    }

    keyVerifyTip.value = '';
  };

  const handleAdd = () => {
    emits('add');
  };

  const handleDelete = () => {
    emits('delete');
  };

  defineExpose<Exposes>({
    getValue() {
      isKeyVerifyPass.value = !!pairInfo.value.key && !keyVerifyTip.value;
      if (!isKeyVerifyPass.value || !valueInputRef.value!.getValue()) {
        return null;
      }

      return {
        [pairInfo.value.key]: pairInfo.value.value,
      };
    },
  });
</script>
<style lang="less" scoped>
  .key-value-pair-main {
    display: flex;
    align-items: center;

    .key-input-wraper {
      position: relative;
      align-self: flex-start;

      .key-input {
        width: 210px;
      }
    }

    .value-input-wraper {
      :deep(.value-input) {
        width: 340px;
        margin-right: 8px;
        margin-left: 14px;
      }
    }

    .error-icon {
      position: absolute;
      top: 10px;
      right: 10px;
      display: flex;
      font-size: 14px;
      color: #ea3636;
    }

    .operation-main {
      font-size: 14px;
      color: #979ba5;
      cursor: pointer;

      .add-icon,
      .delete-icon {
        &:hover {
          color: #63656e;
        }
      }
    }

    .is-not-valid {
      border-color: #ea3636;
    }
  }
</style>
