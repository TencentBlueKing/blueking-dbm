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
  import _ from 'lodash';
  import { computed, ref } from 'vue';

  import TicketModel from '@services/model/ticket/ticket';

  const emits = defineEmits<{
    (e: 'change', value: string): void;
  }>();

  const modelValue = defineModel<string>();

  const statusList = Object.keys(TicketModel.statusTextMap).map((key) => ({
    label: TicketModel.statusTextMap[key as keyof typeof TicketModel.statusTextMap],
    value: key,
  }));

  const isShowDropdown = ref(false);
  const activeItem = computed(() => _.find(statusList, (item) => item.value === modelValue.value));

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
    modelValue.value = item.value;
    emits('change', item.value);
  };
</script>
