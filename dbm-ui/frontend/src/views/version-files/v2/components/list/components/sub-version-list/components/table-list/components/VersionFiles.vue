<template>
  <div
    v-for="(item, index) in data.packages"
    :key="index"
    class="os-limit-column">
    <template v-if="index === 0 || (index !== 0 && isShowMore)">
      <div
        v-overflow-tips
        class="version-file-name">
        {{ item.name }}
      </div>
      <div class="version-tags">
        <BkTag
          v-if="item.permit_os?.length === 1"
          theme="info">
          {{ item.permit_os[0] }}
        </BkTag>
        <BkTag
          v-else-if="!item.permit_os?.length && item.permit_os_type === 'Windows'"
          theme="info">
          {{ `Windows ${t('全部')}` }}
        </BkTag>
        <BkTag
          v-else-if="item.permit_os?.length >= 2"
          v-bk-tooltips="{
            content: item.permit_os?.join('\n'),
          }"
          theme="info">
          {{ `${item.permit_os_type} x ${item.permit_os?.length}` }}
        </BkTag>
        <span v-else></span>
        <BkButton
          v-if="data.packages.length > 1 && index === 0"
          class="ml-6"
          text
          theme="primary"
          @click="handleToggleMoreList">
          {{ isShowMore ? t('收起') : t('+n个文件', { n: data.packages.length - 1 }) }}
        </BkButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbVersionModel from '@services/model/version-file/db-version';

  interface Props {
    data: DbVersionModel;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isShowMore = ref(false);

  const handleToggleMoreList = () => {
    isShowMore.value = !isShowMore.value;
  };
</script>
