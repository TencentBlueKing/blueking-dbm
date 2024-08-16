<template>
  <BkResizeLayout
    class="webconsole-useing-help"
    initial-divide="50%"
    :max="900"
    :min="400"
    placement="right"
    style="height: 100%"
    :trigger-width="20">
    <template #aside>
      <div class="aside-main">
        <Component :is="renderContent" />
      </div>
    </template>
    <template #main>
      <div
        class="empty-main"
        @click="handleClickMain" />
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { DBTypes } from '@common/const';

  import RenderMysqlContent from './RenderMysqlContent.vue';
  import RenderRedisContent from './RenderRedisContent.vue';

  interface Props {
    dbType?: DBTypes;
  }

  interface Emits {
    (e: 'hide'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const emits = defineEmits<Emits>();

  const contentMap = {
    [DBTypes.MYSQL]: RenderMysqlContent,
    [DBTypes.TENDBCLUSTER]: RenderMysqlContent,
    [DBTypes.REDIS]: RenderRedisContent,
  };

  const renderContent = computed(() => contentMap[props.dbType as keyof typeof contentMap]);

  const handleClickMain = () => {
    emits('hide');
  };
</script>
<style lang="less">
  .webconsole-useing-help {
    border: none;

    .bk-resize-layout-aside {
      border: none;

      .bk-resize-trigger:hover {
        border-left: 2px solid #3a84ff;
      }
    }

    .aside-main {
      width: 100%;
      height: 100%;
      padding: 16px;
      font-size: 12px;
      line-height: 23px;
      color: #c4c6cc;
      background: #282829;
      border: 2px solid transparent;
      box-sizing: border-box;
    }

    .empty-main {
      width: 100%;
      height: 100%;
    }
  }
</style>
