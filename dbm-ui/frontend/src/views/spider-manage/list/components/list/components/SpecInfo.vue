<template>
  <BkPopover
    placement="right-start"
    :popover-delay="0"
    theme="light">
    <span class="spec-name">{{ data.name }}</span>
    <template #content>
      <div class="info-wrapper">
        <strong class="info-name">{{ data.name }}</strong>
        <div class="info">
          <span class="info-title">CPU：</span>
          <span class="info-value">({{ data.cpu.min }} ~ {{ data.cpu.max }}) {{ $t('核') }}</span>
        </div>
        <div class="info">
          <span class="info-title">{{ $t('内存') }}：</span>
          <span class="info-value">({{ data.mem.min }} ~ {{ data.mem.max }}) G</span>
        </div>
        <div
          class="info"
          style="align-items: start">
          <span class="info-title">{{ $t('磁盘') }}：</span>
          <span class="info-value">
            <DbOriginalTable
              :border="['row', 'col', 'outer']"
              class="custom-edit-table mt-8"
              :columns="columns"
              :data="data.storage_spec" />
          </span>
        </div>
      </div>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type InstanceSpecInfo } from '@services/model/spider/tendbCluster';

  interface Props {
    data: InstanceSpecInfo;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      field: 'mount_point',
      label: t('挂载点'),
    },
    {
      field: 'size',
      label: t('最小容量G'),
    },
    {
      field: 'type',
      label: t('磁盘类型'),
    },
  ];
</script>

<style lang="less" scoped>
  .spec-name {
    line-height: 18px;
    border-bottom: 1px dashed #979797;
  }

  .info-wrapper {
    width: 530px;
    padding: 9px 2px;
    font-size: 12px;
    color: @default-color;

    .info {
      display: flex;
      align-items: center;
      line-height: 32px;
    }

    .info-name {
      display: inline-block;
      padding-bottom: 12px;
    }

    .info-title {
      width: 60px;
      text-align: right;
      flex-shrink: 0;
    }

    .info-value {
      color: @title-color;
    }
  }
</style>
