<template>
  <BkDropdown
    :is-show="isShowDropdown"
    trigger="manual"
    @hide="handleClose">
    <div
      class="status-trigger"
      :class="{ 'status-trigger-active': isShowDropdown }"
      @click="handleToggle">
      <span>{{ activeItem?.label }}</span>
      <DbIcon type="down-big status-trigger-icon" />
    </div>
    <template #content>
      <BkDropdownMenu>
        <BkDropdownItem
          v-for="item in statusList"
          :key="item.value"
          :class="{ 'dropdown-item-active': item.value === modelValue }"
          @click="handleChangeStatus(item)">
          {{ item.label }}
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { type StatusTypeKeys, StatusTypes } from '@services/model/ticket/ticket';

  const emits = defineEmits<{
    (e: 'change', value: string): void;
  }>();

  const { t } = useI18n();

  const modelValue = defineModel<string>();

  const statusList = Object.keys(StatusTypes).map((key: string) => ({
    label: t(StatusTypes[key as StatusTypeKeys]),
    value: key,
  }));

  const isShowDropdown = ref(false);
  const activeItem = ref();

  const handleToggle = () => {
    isShowDropdown.value = !isShowDropdown.value;
  };

  const handleClose = () => {
    isShowDropdown.value = false;
  };

  const handleChangeStatus = (item: (typeof statusList)[number]) => {
    if (activeItem.value === item) {
      return;
    }
    activeItem.value = item;
    modelValue.value = item.value;
    emits('change', item.value);
  };
</script>
