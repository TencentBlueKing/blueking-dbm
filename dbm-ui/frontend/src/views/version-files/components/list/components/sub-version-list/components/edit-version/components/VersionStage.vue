<template>
  <BkSelect
    v-model="localValue"
    @toggle="handleStageToggle">
    <template #trigger>
      <div
        class="version-stage-trigger"
        :class="{ 'is-active': isShowPanel }">
        <div class="display-main">
          <BkTag
            v-if="displayValue"
            :theme="displayValue?.theme">
            {{ displayValue?.label }}
          </BkTag>
          <span
            v-else
            class="placeholder">
            {{ t('请选择版本阶段') }}
          </span>
        </div>
        <div class="icon-main">
          <DbIcon
            class="trigger-icon"
            type="down-big" />
        </div>
      </div>
    </template>
    <BkOption
      v-for="system in seriesList"
      :key="system.value"
      :label="system.label"
      :value="system.value">
      <BkTag :theme="system.theme">
        {{ system.label }}
      </BkTag>
    </BkOption>
  </BkSelect>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const localValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const isShowPanel = ref(false);
  const seriesList = ref<{ label: string; theme: 'danger' | 'warning' | 'info' | 'success'; value: string }[]>([
    {
      label: 'Alpha',
      theme: 'danger',
      value: 'alpha',
    },
    {
      label: 'Beta',
      theme: 'warning',
      value: 'beta',
    },
    {
      label: 'RC',
      theme: 'info',
      value: 'rc',
    },
    {
      label: 'Release',
      theme: 'success',
      value: 'release',
    },
  ]);

  const displayValue = computed(() => {
    return seriesList.value.find((item) => item.value === localValue.value);
  });

  const handleStageToggle = (isShow: boolean) => {
    isShowPanel.value = isShow;
  };
</script>
<style lang="less">
  .bk-form-item {
    &.is-error {
      .version-stage-trigger {
        border-color: #ea3636;
      }
    }
  }

  .version-stage-trigger {
    display: flex;
    width: 100%;
    height: 32px;
    padding-left: 8px;
    cursor: pointer;
    background: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    align-items: center;
    justify-content: space-between;

    &:hover {
      border-color: #979ba5;
    }

    &.is-active {
      border-color: #3a84ff;

      .icon-main {
        .trigger-icon {
          transform: rotate(180deg);
          transition: transform 0.4s;
        }
      }
    }

    .display-main {
      .placeholder {
        font-size: 12px;
        color: #c4c6cc;
      }
    }

    .icon-main {
      padding-right: 8px;
      font-size: 13px;
      color: #979ba5;

      .trigger-icon {
        display: inline-block;
      }
    }
  }
</style>
