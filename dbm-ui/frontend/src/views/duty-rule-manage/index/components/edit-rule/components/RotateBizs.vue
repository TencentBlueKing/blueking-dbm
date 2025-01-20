<template>
  <BkRadioGroup
    v-model="modelValue"
    class="rotate-bizs-main"
    @change="handleBizChange">
    <div class="biz-box">
      <BkRadio label="all">
        {{ t('全部业务') }}
      </BkRadio>
      <template v-if="modelValue === 'all'">
        <BkButton
          v-if="!showExcludeBizs"
          class="ml-40"
          text
          theme="primary"
          @click="handleAppendExcludeBizs">
          <DbIcon type="add" />
          <span class="ml-3">{{ t('追加排除业务') }}</span>
        </BkButton>
        <div
          v-else
          class="exclude-bizs-main">
          <BkSelect
            v-model="excludeBizs"
            class="exclude-biz-list"
            collapse-tags
            display-key="name"
            enable-virtual-render
            filterable
            id-key="bk_biz_id"
            :list="bizs"
            multiple
            multiple-mode="tag" />
          <div
            class="clear-exclude-icon"
            @click="handleClearSelectedExcludes">
            <DbIcon
              v-bk-tooltips="t('删除排除项')"
              type="delete" />
          </div>
        </div>
      </template>
    </div>
    <div class="biz-box">
      <BkRadio label="partial">
        {{ t('部分业务') }}
      </BkRadio>
      <div
        class="include-biz-list"
        :class="{ 'is-error': !!errorMessage }">
        <BkSelect
          v-if="modelValue === 'partial'"
          v-model="includeBizs"
          collapse-tags
          display-key="name"
          enable-virtual-render
          filterable
          id-key="bk_biz_id"
          :list="bizs"
          multiple
          multiple-mode="tag"
          @change="handleIncludeBizsChange" />
        <div
          v-if="errorMessage"
          class="input-error">
          <DbIcon
            v-bk-tooltips="errorMessage"
            type="exclamation-fill" />
        </div>
      </div>
    </div>
  </BkRadioGroup>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  interface BizConfig {
    biz_config: {
      exclude?: number[];
      include?: number[];
    };
  }

  interface Props {
    data?: BizConfig;
  }

  interface Exposes {
    getValue: () => Promise<BizConfig>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: 'all',
  });

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const showExcludeBizs = ref(false);
  const excludeBizs = ref<number[]>([]);
  const includeBizs = ref<number[]>([]);
  const errorMessage = ref('');

  watch(
    () => props.data?.biz_config,
    (bizConfig) => {
      if (!bizConfig) {
        return;
      }

      if (bizConfig.exclude) {
        excludeBizs.value = bizConfig.exclude;
        modelValue.value = 'all';
        showExcludeBizs.value = true;
      }
      if (bizConfig.include) {
        includeBizs.value = bizConfig.include;
        modelValue.value = 'partial';
      }
    },
    {
      immediate: true,
    },
  );

  const handleIncludeBizsChange = (list: number[]) => {
    if (list.length) {
      errorMessage.value = '';
    }
  };

  const handleAppendExcludeBizs = () => {
    showExcludeBizs.value = true;
  };

  const handleClearSelectedExcludes = () => {
    excludeBizs.value = [];
    showExcludeBizs.value = false;
  };

  const handleBizChange = () => {
    handleClearSelectedExcludes();
    includeBizs.value = [];
  };

  defineExpose<Exposes>({
    getValue() {
      const bizConfig = {};
      if (modelValue.value === 'all' && excludeBizs.value.length) {
        Object.assign(bizConfig, {
          exclude: excludeBizs.value,
        });
      }
      if (modelValue.value === 'partial') {
        if (!includeBizs.value.length) {
          errorMessage.value = t('不能为空');
          return Promise.reject();
        }
        Object.assign(bizConfig, {
          include: includeBizs.value,
        });
      }
      return Promise.resolve({
        biz_config: bizConfig,
      });
    },
  });
</script>
<style lang="less" scoped>
  .rotate-bizs-main {
    width: 100%;
    flex-direction: column;
    gap: 12px;

    .biz-box {
      display: flex;
      width: 100%;
      height: 54px;
      padding-left: 17px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;
      align-items: center;

      :deep(.bk-radio-label) {
        font-size: 12px;
      }

      .exclude-bizs-main {
        flex: 1;
        display: flex;
        margin-left: 36px;
        align-items: center;

        .exclude-biz-list {
          flex: 1;
        }

        .clear-exclude-icon {
          padding: 0 15px 0 12px;
          font-size: 14px;
          color: #979ba5;
          cursor: pointer;
        }
      }

      .include-biz-list {
        position: relative;
        margin-right: 40px;
        margin-left: 36px;
        flex: 1;

        &.is-error {
          :deep(.bk-select-tag) {
            background-color: #fff0f1 !important;

            .angle-down {
              display: none !important;
            }
          }

          .input-error {
            position: absolute;
            top: 0;
            right: 0;
            bottom: 0;
            display: flex;
            padding-right: 10px;
            font-size: 14px;
            color: #ea3636;
            align-items: center;
            cursor: pointer;
          }
        }
      }
    }
  }
</style>
