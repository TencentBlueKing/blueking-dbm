<template>
  <EditableColumn
    class="role-column"
    :label="t('角色类型')"
    readonly
    :width="200">
    <EditableBlock :placeholder="t('输入主机后自动生成')">
      <div class="role-item">
        {{ host.instance_role ? host.instance_role.split('_')[1] : '' }}
      </div>
      <div
        v-if="host.pair_machine.ip"
        class="role-item">
        slave
      </div>
    </EditableBlock>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    host: {
      instance_role: string;
      ip: string;
      pair_machine: {
        ip: string;
      };
    };
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .role-column {
    :deep(.bk-editable-block-content-wrapper) {
      padding: 0;
      margin: 0;

      .bk-editable-block-content-placeholder {
        padding: 0 10px;
      }
    }

    .role-item {
      height: 40px;
      padding: 0 10px;
      line-height: 40px;

      &:not(:first-child) {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
