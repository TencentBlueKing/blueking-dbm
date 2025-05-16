<template>
  <BkCollapse
    v-model="activeIndex"
    class="flow-collapse-main"
    :class="{ 'is-danger': danger }">
    <BkCollapsePanel :name="name">
      <template #header>
        <div class="collapse-panel-header">
          <DbIcon
            :class="{ 'active-icon': isPanelActive }"
            type="down-shape" />
          <slot
            v-if="slots.header"
            name="header" />
          <span
            v-else
            class="table-title">
            {{ title }}
          </span>
        </div>
      </template>
      <template #content>
        <slot />
      </template>
    </BkCollapsePanel>
  </BkCollapse>
</template>
<script setup lang="ts">
  interface Props {
    danger?: boolean;
    name?: string;
    title?: string;
  }

  interface Slots {
    default: any;
    header: any;
  }

  const props = withDefaults(defineProps<Props>(), {
    danger: false,
    name: 'default',
    title: '',
  });

  const slots = defineSlots<Slots>();

  const activeIndex = ref([props.name]);

  const isPanelActive = computed(() => !activeIndex.value.includes(props.name));
</script>
<style lang="less">
  .flow-collapse-main {
    &.is-danger {
      .bk-collapse-item {
        background: #fff0f0;
      }
    }

    width: 100%;
    max-width: 580px;
    margin-top: 12px;

    .bk-collapse-item {
      background: #f5f7fa;
      border-radius: 2px;
    }

    .bk-collapse-content {
      padding: 0 18px 16px;
    }

    .collapse-panel-header {
      position: relative;
      display: flex;
      height: 38px;
      padding-left: 14px;
      color: #4d4f56;
      cursor: pointer;
      align-items: center;

      .db-icon-down-shape {
        transform: rotateZ(0deg);
        transition: all 0.5s;
      }

      .table-title {
        margin-left: 8px;
        font-size: 12px;
        font-weight: 700;
      }

      .active-icon {
        transform: rotateZ(-90deg);
        transition: all 0.5s;
      }
    }
  }
</style>
