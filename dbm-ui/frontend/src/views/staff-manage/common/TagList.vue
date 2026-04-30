<template>
  <BkTag
    v-for="(item, index) in tagList"
    :key="item.value"
    :closable="closeable"
    :theme="item.theme"
    @close="() => handleClose(index)">
    {{ item.label }}
  </BkTag>
</template>

<script setup lang="ts">
  interface Props {
    closeable?: boolean;
    list: {
      label: string;
      value: number | string;
    }[];
  }

  type Emits = (e: 'close', index: number) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const themeMap = {
    '0': 'success',
    '1': 'info',
    '2': 'warning',
    '3': 'danger',
  } as const;

  const tagList = computed(() =>
    props.list.map((item, index) => ({
      ...item,
      theme: themeMap[String(index % 4) as keyof typeof themeMap],
    })),
  );

  const handleClose = (index: number) => {
    emits('close', index);
  };
</script>
