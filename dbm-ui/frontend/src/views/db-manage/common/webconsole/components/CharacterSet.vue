<template>
  <div class="operate-item">
    <div class="operate-item-inner">
      <BkSelect
        v-model="modelValue"
        :input-search="false"
        :list="list"
        :popover-min-width="200"
        filterable>
        <template #trigger="{ selected }">
          <div
            class="character-set-trigger"
            @click="() => (isActive = !isActive)">
            <DbIcon
              class="operate-icon character-set-prefix"
              type="bk-dbm-icon db-icon-wenjian" />
            <div>{{ selected?.[0]?.label || '' }}</div>
            <DbIcon
              class="operate-icon character-set-append"
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
  const modelValue = defineModel<string>({
    required: true,
  });

  const list = [
    { label: 'default', value: 'default' },
    { label: 'latin1', value: 'latin1' },
    { label: 'utf8', value: 'utf8' },
    { label: 'utf8mb4', value: 'utf8mb4' },
    { label: 'gbk', value: 'gbk' },
    { label: 'gb2312', value: 'gb2312' },
  ];

  const isActive = ref(false);
</script>
<style lang="less" scoped>
  .character-set-trigger {
    position: relative;
    display: flex;
    width: 94px;
    height: 28px;
    align-items: center;
    justify-content: center;

    .character-set-prefix,
    .character-set-append {
      position: absolute;
    }

    .character-set-prefix {
      left: 0;
    }

    .character-set-append {
      right: 0;
    }

    .db-icon-up {
      transform: rotate(180deg);
      transition: all 0.2s;
    }
  }
</style>
