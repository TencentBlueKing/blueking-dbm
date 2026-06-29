<template>
  <div class="biz-staff-manage-operation-record">
    <OperationRecord />
  </div>
</template>
<script setup lang="ts">
  import OperationRecord from '@views/staff-manage/common/operation-record/Index.vue';

  const router = useRouter();

  router.replace({
    params: {
      subTabType: '',
      tabType: 'oplog',
    },
  });
</script>

<style lang="less">
  .biz-staff-manage-operation-record {
    padding: 20px 24px;
  }
</style>
