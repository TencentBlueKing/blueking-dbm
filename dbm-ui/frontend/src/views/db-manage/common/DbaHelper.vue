<template>
  <Teleport
    :disabled="userDBAList.length === 0"
    to="#dbContentHeaderAppend">
    <div class="pr-16 db-manage-dba-header">
      <span class="pr-8">{{ t('主DBA') }}:</span>
      <a
        class="dba-item"
        :href="`wxwork://message?username=${userDBAList[0]}`">
        <DbIcon
          svg
          type="qw" />
        <span class="pl-4">
          {{ userDBAList[0] }}
        </span>
      </a>
      <template v-if="userDBAList[1]">
        <span class="pr-8 ml-16">{{ t('备DBA') }}:</span>
        <a
          class="dba-item"
          :href="`wxwork://message?username=${userDBAList[1]}`">
          <DbIcon
            svg
            type="qw" />
          <span class="pl-4">
            {{ userDBAList[1] }}
          </span>
        </a>
      </template>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { DBTypes } from '@common/const';

  import useUserDBAList from '@views/db-manage/hooks/useDBAList';

  const route = useRoute();
  const { t } = useI18n();

  const dbType = ref<DBTypes>();

  const userDBAList = useUserDBAList(dbType);

  watch(
    route,
    () => {
      dbType.value = route.meta.dbType as DBTypes;
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .db-manage-dba-header {
    display: flex;
    margin-left: auto;
    font-size: 12px;
    line-height: 20px;
    color: #313238;
    align-items: center;

    .dba-item {
      display: flex;
      align-items: center;
      color: #3a84ff;
    }
  }
</style>
