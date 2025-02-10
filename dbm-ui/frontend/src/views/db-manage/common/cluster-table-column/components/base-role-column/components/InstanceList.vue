<template>
  <div>
    <div
      class="mb-16"
      style="display: flex">
      <BkButton
        class="mr-8"
        @click="handleCopyAbnormal">
        {{ t('复制异常实例') }}({{ abnormalCount }})
      </BkButton>
      <BkButton
        class="mr-8"
        @click="handleCopyAll">
        {{ t('复制所有实例') }}({{ totalCount }})
      </BkButton>
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="t('搜索实例')"
        type="search" />
    </div>
    <BkTable
      :column-config="{ resizable: true }"
      :data="renderData"
      :height="440"
      :scroll-y="{ enabled: true, gt: 0 }"
      show-overflow
      size="mini">
      <BkTableColumn :label="t('实例')">
        <template #default="{ data: rowData }: { data: Props['data'][number] }">
          {{ rowData.ip }}:{{ rowData.port }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('部署角色')"
        width="30%">
        {{ role }}
      </BkTableColumn>
      <BkTableColumn
        :label="t('状态')"
        :width="160">
        <template #default="{ data: rowData }: { data: Props['data'][number] }">
          <ClusterInstanceStatus :data="rowData.status" />
        </template>
      </BkTableColumn>
    </BkTable>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useDebouncedRef } from '@hooks';

  import { ClusterInstStatusKeys } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  interface Props {
    data: {
      ip: string;
      port: number;
      status: string;
      shard_id?: string;
    }[];
    role: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const searchKey = useDebouncedRef('');
  const abnormalCount = ref(0);
  const totalCount = ref(0);

  const renderData = computed(() =>
    _.filter(props.data, (item) => item.ip.includes(searchKey.value) || `${item.port}`.includes(searchKey.value)),
  );

  watch(
    renderData,
    () => {
      abnormalCount.value = 0;
      totalCount.value = renderData.value.length;
      renderData.value.forEach((item) => {
        if (item.status !== ClusterInstStatusKeys.RUNNING) {
          abnormalCount.value += 1;
        }
      });
    },
    {
      immediate: true,
    },
  );

  /**
   * 复制异常实例
   */
  const handleCopyAbnormal = () => {
    const abnormalInstanceList = props.data
      .filter((item) => item.status !== ClusterInstStatusKeys.RUNNING)
      .map((item) => `${item.ip}:${item.port}`);
    if (abnormalInstanceList.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(abnormalInstanceList.join('\n'), t('复制成功，共n条', { n: abnormalInstanceList.length }));
  };

  /**
   * 复制所有实例
   */
  const handleCopyAll = () => {
    const instanceList = props.data.map((item) => `${item.ip}:${item.port}`);
    if (instanceList.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(instanceList.join('\n'), t('复制成功，共n条', { n: instanceList.length }));
  };
</script>
