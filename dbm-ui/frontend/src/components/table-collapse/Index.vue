<template>
  <BkCollapse
    v-model="activeIndex"
    class="table-collapse-main">
    <BkCollapsePanel :name="name">
      <template #header>
        <div class="collapse-panel-header">
          <span class="panel-title">
            {{ title }}
          </span>
          <DbIcon
            :class="{ 'active-icon': isPanelActive }"
            type="down-big" />
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
    name?: string;
    title?: string;
  }

  interface Slots {
    default: any;
    header: any;
  }

  const props = withDefaults(defineProps<Props>(), {
    name: 'default',
    title: '',
  });

  defineSlots<Slots>();

  const activeIndex = ref([props.name]);

  const isPanelActive = computed(() => !activeIndex.value.includes(props.name));
</script>
<style lang="less" scoped>
  .table-collapse-main {
    :deep(.collapse-panel-header) {
      position: relative;
      display: flex;
      height: 28px;
      padding: 0 12px 0 16px;
      color: #313238;
      cursor: pointer;
      background: #f0f1f5;
      align-items: center;
      justify-content: space-between;

      .db-icon-down-shape {
        color: #979ba5;
        transform: rotateZ(0deg);
        transition: all 0.5s;
      }

      .panel-title {
        font-size: 12px;
        font-weight: 700;
      }

      .active-icon {
        transform: rotateZ(-90deg);
        transition: all 0.5s;
      }
    }

    :deep(.bk-collapse-content) {
      padding: 0;
    }
  }
</style>
