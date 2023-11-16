<template>
  <BkSideslider
    v-model="modelValue"
    :width="1100">
    <div class="inspection-instance-detail">
      <div class="wrapper-left">
        <BkInput />
        <div class="instance-list">
          <div class="instance-item">
            asdasdasd
          </div>
        </div>
      </div>
      <div class="wrapper-right">
        <BkTable :columns="tableColumns" />
      </div>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<boolean>({
    default: false,
  });

  const tableColumns = [
    {
      label: t('库名'),
    },
    {
      label: t('表名'),
    },
  ];
</script>
<style lang="postcss">
.inspection-instance-detail {
  display: flex;

  .wrapper-left{
    flex: 0 0 320px;
    display: flex;
    padding: 16px;
    background-color: #F5F7FA;

    .instance-item{
      display: flex;
      height: 32px;
      padding: 0 12px;
      font-size: 12px;
      color: #63656E;
      background: #fff;
      border: 1px solid transparent;
      border-radius: 2px;
      align-items: center;

      & ~ .instance-item{
        margin-top: 8px;
        font-size: 12px;
      }

      &:hover{
        border-color: #3A84FF;
      }

      &.active{
        font-weight: bold;
        color: #3A84FF;
        border-color: #3A84FF;
      }
    }
  }
}
</style>
