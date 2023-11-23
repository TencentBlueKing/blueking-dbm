<template>
  <BkSideslider
    v-model:is-show="modelValue"
    :title="t('失败的从库实例详情')"
    :width="1100">
    <BkLoading :loading="isLoading">
      <div class="inspection-instance-detail">
        <div class="wrapper-left">
          <BkInput v-model="searchKey" />
          <div class="instance-list">
            <div
              v-for="item in renderList"
              :key="item.id"
              class="instance-item"
              :class="{
                active: item.id === activeKey,
              }"
              @click="handleActive(item)">
              {{ item.ip }}:{{ item.port }}
            </div>
          </div>
        </div>
        <div class="wrapper-right">
          <div class="header">
            {{ activeItem?.master_ip }}:{{ activeItem?.port }}（主）
            ->
            {{ activeItem?.ip }}:{{ activeItem?.port }}（从）
          </div>
          <BkTable :columns="tableColumns" />
        </div>
      </div>
    </BkLoading>
  </BkSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import {
    computed,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getChecksumInstance } from '@services/report';

  import { useDebouncedRef } from '@hooks';

  import { encodeRegexp } from '@utils';

  const props = defineProps<Props>();

  const { t } = useI18n();

  interface Props {
    id: number
  }
  const modelValue = defineModel<boolean>({
    default: false,
  });

  const searchKey = useDebouncedRef('');
  const activeKey = ref(0);
  const instanceList = shallowRef<ServiceReturnType<typeof getChecksumInstance>['results']>([]);

  const activeItem = computed(() => _.find(instanceList.value, item => item.id === activeKey.value));
  const renderList = computed(() => {
    const rule = new RegExp(encodeRegexp(searchKey.value), 'i');
    return instanceList.value.filter(item => rule.test(item.ip));
  });

  const tableColumns = [
    {
      label: t('库名'),
    },
    {
      label: t('表名'),
    },
  ];

  const {
    loading: isLoading,
    run: fetchInstanceList,
  } = useRequest(getChecksumInstance, {
    manual: true,
    onSuccess(data) {
      instanceList.value = data.results;
      if (instanceList.value.length > 0) {
        activeKey.value = instanceList.value[0].id;
      }
    },
  });

  watch(modelValue, () => {
    if (!modelValue.value || !props.id) {
      return;
    }
    fetchInstanceList({
      report_id: props.id,
      offset: 0,
      limit: -1,
    });
  });

  const handleActive = (data: UnwrapRef<typeof instanceList>[number]) => {
    activeKey.value = data.id;
  };
</script>
<style lang="less">
.inspection-instance-detail {
  display: flex;

  .wrapper-left{
    height: calc(100vh - 52px);
    padding: 16px;
    background-color: #F5F7FA;
    flex: 0 0 320px;

    .instance-list{
      height: calc(100% - 60px);
      margin-top: 12px;
      overflow-y: auto;
    }

    .instance-item{
      display: flex;
      height: 32px;
      padding: 0 12px;
      font-size: 12px;
      color: #63656E;
      cursor: pointer;
      background: #fff;
      border: 1px solid transparent;
      border-radius: 2px;
      align-items: center;
      transition: all .1s;

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

  .wrapper-right{
    padding: 24px;
    background: #fff;

    .header{
      display: flex;
      height: 36px;
      padding: 0 24px;
      font-size: 12px;
      font-weight: bold;
      color: #63656E;
      background: #F0F1F5;
      border-radius: 2px;
      align-items: center;
    }

    .bk-table .bk-table-head table thead th{
      background: #FAFBFD;
    }
  }
}
</style>
