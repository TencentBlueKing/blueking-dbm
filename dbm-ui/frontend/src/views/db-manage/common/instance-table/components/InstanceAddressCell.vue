<template>
  <div
    :class="{
      'is-hover': isHover,
    }">
    <TextOverflowLayout>
      <TextHighlight
        high-light-color="#F59500"
        :keyword="searchKeyword">
        {{ data.instance_address }}
      </TextHighlight>
      <template #append>
        <slot
          name="append"
          v-bind="{ data: data }" />
        <BkTag
          v-if="data.isNew"
          class="ml-4"
          size="small"
          theme="success">
          NEW
        </BkTag>
        <PopoverCopy @toogle-show="handlePopoverShow">
          <div @click="handleCopy(data.instance_address)">
            {{ t('复制实例') }}
          </div>
          <div @click="handleCopy(data.ip)">
            {{ t('复制 IP') }}
          </div>
        </PopoverCopy>
      </template>
    </TextOverflowLayout>
  </div>
</template>
<script setup lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  import type { ClusterTypeRelateInstanceModel, ISupportClusterType } from '../types';

  export interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: ISupportClusterType;
    data: ValueOf<ClusterTypeRelateInstanceModel>;
  }

  export interface Slots {
    append?: (params: { data: ValueOf<ClusterTypeRelateInstanceModel> }) => VNode;
  }

  defineProps<Props>();
  defineSlots<Slots>();

  const { t } = useI18n();
  const route = useRoute();

  const searchKeyword = ref('');

  const isHover = ref(false);

  watch(
    route,
    () => {
      searchKeyword.value = (route.query.instance_address as string) || '';
    },
    {
      immediate: true,
    },
  );

  const handleCopy = (data: string) => {
    execCopy(
      data,
      t('复制成功，共n条', {
        n: 1,
      }),
    );
  };

  const handlePopoverShow = (value: boolean) => {
    isHover.value = value;
  };
</script>
