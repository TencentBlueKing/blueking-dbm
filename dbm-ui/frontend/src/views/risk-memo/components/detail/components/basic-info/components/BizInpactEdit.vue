<template>
  <div
    class="biz-edit-value-main"
    :class="{ 'is-error': isError }">
    <div
      v-if="!isEdit"
      class="display-mian">
      <TagBlock
        class="value-display"
        :data="renderTags"
        :style="{ width: `${value.length * 46}px` }" />
      <AuthTemplate
        v-if="!readonly"
        action-id="risk_memo_manage"
        :biz-id="bizId"
        :permission="managePermission">
        <DbIcon
          class="edit-main"
          type="edit"
          @click="handleClickEdit" />
      </AuthTemplate>
    </div>
    <BkSelect
      v-else
      ref="editValueRef"
      v-model="localValue"
      class="tags-select"
      :clearable="false"
      collapse-tags
      :list="effectBizLabels"
      multiple
      multiple-mode="tag"
      show-on-init
      @change="handleSelectChange"
      @toggle="handleSelectToggle" />
    <DbIcon
      v-if="isError"
      v-bk-tooltips="t('不能为空')"
      class="error-icon"
      type="exclamation-fill" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBizInpactList } from '@services/source/riskMemo';

  import TagBlock from '@components/tag-block/Index.vue';

  interface Props {
    bizId?: number;
    managePermission?: boolean;
    readonly?: boolean;
    value?: string[];
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    bizId: 0,
    managePermission: true,
    readonly: false,
    value: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editValueRef = ref(null);
  const isEdit = ref(false);
  const localValue = ref<string[]>([]);
  const isError = ref(false);

  const renderTags = computed(() => {
    if (!effectBizLabels.value) {
      return [];
    }

    const selectListMap = effectBizLabels.value.reduce<Record<string, string>>(
      (dataMap, item) =>
        Object.assign(dataMap, {
          [item.value]: item.label,
        }),
      {},
    );
    return localValue.value.map((item) => selectListMap[item]);
  });

  const { data: effectBizLabels } = useRequest(getBizInpactList);

  watch(
    () => props.value,
    () => {
      localValue.value = props.value;
    },
    {
      immediate: true,
    },
  );

  const handleClickEdit = () => {
    isEdit.value = true;
  };

  const handleSelectChange = () => {
    isError.value = false;
  };

  const handleSelectToggle = (isShow: boolean) => {
    if (!isShow) {
      if (!localValue.value.length) {
        isError.value = true;
        return;
      }

      if (localValue.value.join(',') !== props.value.join(',')) {
        emits('change', localValue.value.join(','));
      }
      isEdit.value = false;
    }
  };
</script>
<style lang="less">
  .biz-edit-value-main {
    position: relative;
    display: flex;
    width: 100%;
    font-size: 12px;
    align-items: center;

    &.is-error {
      .bk-select-tag {
        border-color: #ea3636 !important;
      }

      .angle-down {
        display: none !important;
      }
    }

    .display-mian {
      display: flex;
      width: 100%;

      .value-display {
        max-width: calc(100% - 120px);
        overflow: hidden;

        .bk-tag {
          padding: 1px 8px;
        }
      }

      .tags-display {
        min-width: 100px;
      }

      .edit-main {
        display: block;
        margin-top: 7px;
        margin-left: 4px;
        font-size: 12px;
        color: #979ba5;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .tags-select {
      width: 100%;
    }

    .error-icon {
      position: absolute;
      top: 50%;
      right: 8px;
      z-index: 9;
      font-size: 14px;
      color: #ea3636;
      cursor: pointer;
      transform: translateY(-50%);
    }
  }
</style>
