<template>
  <BkFormItem
    :label="t('园区')"
    property="details.sub_zone_ids"
    required
    :rules="itemInfo.rules">
    <BkLoading :loading="loading">
      <div class="apply-subzones">
        <Component
          :is="itemInfo.content"
          ref="subzoneRef"
          v-model="modelValue"
          :city-code="cityCode"
          :subzone-list="subzoneList" />
      </div>
    </BkLoading>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasSubzonesByCity } from '@services/source/infras';

  import { Affinity } from '@common/const';

  import RandomFixed from './components/RandomFixed.vue';
  import RandomSelectableOrMultiple from './components/RandomSelectableOrMultiple.vue';
  import RandomSelectableOrSingle from './components/RandomSelectableOrSingle.vue';
  import Single from './components/Single.vue';

  interface Props {
    cityCode: string;
    disasterToleranceLevel: string;
  }

  interface Expose {
    setInitSubzone(subzoneIds: number[]): void;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number[]>({
    required: true,
  });

  enum ContentItemKey {
    DEFAULT = 'DEFAULT',
    RANDOM_FIXED = 'RANDOM_FIXED',
    RANDOM_SELECTABLE_OR_MULTIPLE = 'RANDOM_SELECTABLE_OR_MULTIPLE',
    RANDOM_SELECTABLE_OR_SINGLE = 'RANDOM_SELECTABLE_OR_SINGLE',
    SINGLE = 'SINGLE',
  }

  const { t } = useI18n();

  const subzoneRef = useTemplateRef<{ setInitSubzone?: (subzoneIds: number[]) => void }>('subzoneRef');

  const itemKey = computed(() => {
    if (props.disasterToleranceLevel === Affinity.CROS_SUBZONE) {
      return ContentItemKey.RANDOM_SELECTABLE_OR_MULTIPLE;
    }
    if (props.disasterToleranceLevel === Affinity.SAME_SUBZONE_CROSS_SWTICH) {
      return ContentItemKey.SINGLE;
    }
    if (props.disasterToleranceLevel === Affinity.NONE && props.cityCode !== 'default') {
      return ContentItemKey.RANDOM_SELECTABLE_OR_SINGLE;
    }
    if (
      [Affinity.CROSS_RACK, Affinity.MAX_EACH_ZONE_EQUAL].includes(props.disasterToleranceLevel as Affinity) ||
      (props.disasterToleranceLevel === Affinity.NONE && props.cityCode === 'default')
    ) {
      return ContentItemKey.RANDOM_FIXED;
    }
    return ContentItemKey.DEFAULT;
  });

  const itemInfo = computed(() => {
    const infoMap = {
      [ContentItemKey.DEFAULT]: {
        content: null,
        rules: [],
      },
      [ContentItemKey.RANDOM_FIXED]: {
        content: RandomFixed,
        rules: [
          {
            required: true,
            trigger: 'change',
            validator: () => true,
          },
        ],
      },
      [ContentItemKey.RANDOM_SELECTABLE_OR_MULTIPLE]: {
        content: RandomSelectableOrMultiple,
        rules: [
          {
            required: true,
            trigger: 'change',
            validator: (value: number[]) => {
              if (value.length === 0) {
                return true;
              }
              return value.length >= 2 ? true : Promise.resolve(t('至少选择n个区', { n: 2 }));
            },
          },
        ],
      },
      [ContentItemKey.RANDOM_SELECTABLE_OR_SINGLE]: {
        content: RandomSelectableOrSingle,
        rules: [
          {
            required: true,
            trigger: 'change',
            validator: (value: number[]) => {
              if (value.length === 0) {
                return true;
              }
              return value.length >= 1 ? true : Promise.resolve(t('园区不能为空'));
            },
          },
        ],
      },
      [ContentItemKey.SINGLE]: {
        content: Single,
        rules: [
          {
            trigger: 'change',
            validator: (value: number[]) => value.length !== 0,
          },
        ],
      },
    };

    return infoMap[itemKey.value];
  });

  const {
    data: subzoneList,
    loading,
    run: runGetInfrasSubzonesByCity,
  } = useRequest(getInfrasSubzonesByCity, {
    manual: true,
  });

  watch(
    () => [props.disasterToleranceLevel, props.cityCode],
    () => {
      modelValue.value = [];
    },
  );

  watch(
    () => props.cityCode,
    () => {
      if (props.cityCode) {
        runGetInfrasSubzonesByCity({
          city_code: props.cityCode,
        });
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Expose>({
    setInitSubzone(subzoneIds: number[]) {
      subzoneRef.value!.setInitSubzone?.(subzoneIds);
    },
  });
</script>

<style lang="less">
  .apply-subzones {
    display: flex;
    align-items: center;

    .subzone-bar {
      width: 1px;
      height: 13px;
      margin: 0 12px;
      border: 1px solid #c4c6cc;
    }

    .bk-checkbox {
      position: relative;
      // display: flex;

      & ~ .bk-checkbox {
        margin-left: 4px;
      }

      &.is-checked {
        .bk-checkbox-input {
          display: inline-block;
        }
      }

      .bk-checkbox-input {
        position: absolute;
        top: 0;
        left: 0;
        display: none;
        width: 14px;
        height: 14px;
      }

      .bk-checkbox-label {
        width: 100px;
        margin-left: 0;
        text-align: center;
        background: #f5f7fa;
        border-radius: 2px;

        // &:hover {
        //   color: #3a84ff;
        // }
      }
    }

    .bk-radio {
      position: relative;
      // display: flex;

      & ~ .bk-radio {
        margin-left: 4px;
      }

      &.is-checked {
        .bk-radio-input {
          display: inline-block;

          &::after {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 4px;
            height: 8px;
            border: 2px solid #fff;
            border-top: 0;
            border-left: 0;
            content: '';
            transform: translate(-50%, -60%) scaleY(1) rotate(45deg);
            transform-origin: center;
          }
        }

        .bk-radio-label {
          color: #3a84ff;
          background: #f0f5ff;
        }
      }

      .bk-radio-input {
        position: absolute;
        top: 0;
        left: 0;
        display: none;
        width: 14px;
        height: 14px;
        vertical-align: middle;
        background: var(--primary-color);
        border: 1px solid #979ba5;
        border-color: var(--primary-color);
        border-radius: 2px;
        transition: all 0.1s;
      }

      .bk-radio-label {
        width: 100px;
        margin-left: 0;
        font-size: 12px;
        text-align: center;
        background: #f5f7fa;
        border-radius: 2px;

        &:hover {
          color: #3a84ff;
        }
      }
    }
  }
</style>
