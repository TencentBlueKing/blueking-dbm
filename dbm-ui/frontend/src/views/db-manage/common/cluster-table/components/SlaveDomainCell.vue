<template>
  <div v-if="data.slaveEntryList.length > 0">
    <TextOverflowLayout>
      <div
        v-for="slaveItem in data.slaveEntryList.slice(0, renderCount)"
        :key="slaveItem.entry"
        style="line-height: 26px">
        <TextHighlight
          high-light-color="#F59500"
          :keyword="searchKeyword">
          {{ slaveItem.entry }}:{{ slaveItem.port }}
        </TextHighlight>
      </div>
      <template #append>
        <PopoverCopy>
          <div @click="handleCopyDomain">
            {{ t('复制域名') }}
          </div>
          <div @click="handleCopyDomainPort">
            {{ t('复制域名:端口') }}
          </div>
        </PopoverCopy>
      </template>
    </TextOverflowLayout>
  </div>
  <span v-if="data.slaveEntryList.length < 1">--</span>
  <div v-if="data.slaveEntryList.length > renderCount">
    <span>... </span>
    <BkPopover
      placement="top"
      theme="light">
      <BkTag>
        <I18nT keypath="共n个">{{ data.slaveList.length }}</I18nT>
      </BkTag>
      <template #content>
        <div style="max-height: 280px; overflow: scroll">
          <div
            v-for="slaveItem in data.slaveEntryList"
            :key="slaveItem.entry"
            style="line-height: 20px">
            {{ slaveItem.entry }}:{{ slaveItem.port }}
          </div>
        </div>
      </template>
    </BkPopover>
  </div>
</template>
<script lang="ts">
  import _ from 'lodash';
  import { useRoute } from 'vue-router';

  import { ClusterTypes } from '@common/const';

  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  import { t } from '@locales/index';

  import type { ClusterModel } from '../types';

  export type ISupportClusterType =
    | ClusterTypes.TENDBCLUSTER
    | ClusterTypes.TENDBHA
    | ClusterTypes.REDIS_INSTANCE
    | ClusterTypes.SQLSERVER_HA;

  export const copyDomain = (data: ClusterModel<ISupportClusterType>['slaveEntryList']) => {
    const copyList = _.uniq(data.map(({ entry }) => entry));
    execCopy(
      copyList.join('\n'),
      t('复制成功，共n条', {
        n: copyList.length,
      }),
    );
  };

  export const copyDomainPort = (data: ClusterModel<ISupportClusterType>['slaveEntryList']) => {
    const copyList = _.uniq(data.map(({ entry, port }) => `${entry}:${port}`));
    execCopy(
      copyList.join('\n'),
      t('复制成功，共n条', {
        n: copyList.length,
      }),
    );
  };
</script>
<script setup lang="ts">
  interface Props {
    data: ClusterModel<ISupportClusterType>;
  }

  const props = defineProps<Props>();

  const route = useRoute();

  const renderCount = 6;

  const searchKeyword = ref('');

  watch(
    route,
    () => {
      searchKeyword.value = (route.query.domain as string) || '';
    },
    {
      immediate: true,
    },
  );

  const handleCopyDomain = () => {
    copyDomain(props.data.slaveEntryList);
  };

  const handleCopyDomainPort = () => {
    copyDomainPort(props.data.slaveEntryList);
  };
</script>
