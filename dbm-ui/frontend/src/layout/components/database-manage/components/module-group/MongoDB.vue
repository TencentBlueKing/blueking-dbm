<template>
  <FunController module-id="mongodb">
    <BkMenuGroup name="MongoDB">
      <BkSubmenu
        :title="t('集群管理')">
        <template #icon>
          <DbIcon type="cluster" />
        </template>
        <BkMenuItem key="MongoDBReplicaSetList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('副本集集群') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="MongoDBSharedClusterList">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('分片集群') }}
          </span>
        </BkMenuItem>
        <BkMenuItem key="mongodbInstance">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('实例视图') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
      <BkSubmenu
        key="mongodb-permission"
        :title="t('权限管理')">
        <template #icon>
          <DbIcon type="history" />
        </template>
        <BkMenuItem key="MongodbPermission">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ t('授权规则') }}
          </span>
        </BkMenuItem>
      </BkSubmenu>
    </BkMenuGroup>
  </FunController>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

</script>
