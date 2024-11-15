<template>
  <BkSelect
    v-model="modelValue"
    :filterable="false"
    @change="handleChooseType"
    @toggle="handleTogglePopover">
    <template #trigger>
      <div :class="triggerClassName">
        <span class="label-content">
          <BkButton
            class="mr-4"
            :style="{ color: titleColor }"
            text>
            {{ currentTitle }}
          </BkButton>
          <DbIcon
            class="more-icon"
            :class="{
              'more-icon-active': isRotate,
            }"
            :type="iconType" />
        </span>
      </div>
    </template>
    <BkOption
      v-for="item in dropdownList"
      :id="item.value"
      :key="item.value"
      :name="item.label" />
  </BkSelect>
</template>

<script lang="ts">
  export enum FilterType {
    EXACT = 'EXACT',
    CONTAINS = 'CONTAINS',
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    titleColor: string;
    iconType: string;
    triggerClassName: string;
  }

  defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const dropdownList = [
    {
      label: t('精确搜索'),
      value: FilterType.EXACT,
    },
    {
      label: t('模糊搜索'),
      value: FilterType.CONTAINS,
    },
  ];

  const isRotate = ref(false);

  const currentTitle = computed(() =>
    modelValue.value === FilterType.EXACT ? dropdownList[0].label : dropdownList[1].label,
  );

  const handleChooseType = (type: string) => {
    modelValue.value = type;
  };

  const handleTogglePopover = (isShow: boolean) => {
    isRotate.value = isShow;
  };
</script>
