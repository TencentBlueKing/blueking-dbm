<template>
  <div class="operate-item">
    <div class="operate-item-inner">
      <BkSelect
        v-model="modelValue"
        :input-search="false"
        :list="list">
        <template #trigger="{ selected }">
          <div
            class="role-select-trigger"
            @click="() => (isActive = !isActive)">
            <div>{{ selected?.[0]?.label || '' }}</div>
            <DbIcon
              class="operate-icon role-select-append"
              :class="{
                'db-icon-up': isActive,
              }"
              type="bk-dbm-icon db-icon-down-big" />
          </div>
        </template>
      </BkSelect>
    </div>
  </div>
</template>
<script lang="ts" setup>
  interface Props {
    list: {
      label: string;
      value: string;
    }[];
  }

  defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const isActive = ref(false);
</script>
<style lang="less" scoped>
  .role-select-trigger {
    position: relative;
    display: flex;
    width: 72px;
    height: 28px;
    align-items: center;

    .role-select-prefix,
    .role-select-append {
      position: absolute;
    }

    .role-select-prefix {
      left: 0;
    }

    .role-select-append {
      right: 0;
    }

    .db-icon-up {
      transform: rotate(180deg);
      transition: all 0.2s;
    }
  }
</style>
