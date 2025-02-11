<template>
  <BkSideslider
    v-model:is-show="modelValue"
    render-directive="if"
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
            {{ activeItem?.master_ip }}:{{ activeItem?.port }}（主） -> {{ activeItem?.ip }}:{{
              activeItem?.port
            }}（从）
          </div>
          <BkTable
            :columns="tableColumns"
            :data="tableData" />
        </div>
      </div>
    </BkLoading>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { computed, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getChecksumInstance } from '@services/source/report';

  import { useDebouncedRef } from '@hooks';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { calcTextHeight, encodeRegexp } from '@utils';

  const props = defineProps<Props>();

  const { t } = useI18n();

  interface IDataRow {
    db_name: string;
    table_name: string;
  }

  interface Props {
    id: number;
  }
  const modelValue = defineModel<boolean>({
    default: false,
  });

  const isTextOverflow = ref<Record<string, boolean>>({})
  const searchKey = useDebouncedRef('');
  const activeKey = ref(0);
  const instanceList = shallowRef<ServiceReturnType<typeof getChecksumInstance>['results']>([]);
  const tableData = shallowRef<IDataRow[]>([]);
  const activeItem = computed(() => _.find(instanceList.value, (item) => item.id === activeKey.value));
  const renderList = computed(() => {
    const rule = new RegExp(encodeRegexp(searchKey.value), 'i');
    return instanceList.value.filter((item) => rule.test(item.ip));
  });

  const tableColumns = [
    {
      label: t('库名'),
      field: 'db_name',
      minWidth: 220,
      render: ({ data }: { data: IDataRow }) => (
        <TextOverflowLayout>
          {{
            default: () => data.db_name
          }}
        </TextOverflowLayout>
      )
    },
    {
      label: t('表名'),
      field: 'table_name',
      render: ({ data, index }: { data: IDataRow, index: number }) => (
        <p
          class="table-name"
          row-key={`row-${index}`}
          v-bk-tooltips={{
            content: data.table_name,
            disabled: !isTextOverflow.value[`row-${index}`],
          }}>
          {data.table_name}
        </p>
      )
    },
  ];

  const { loading: isLoading, run: fetchInstanceList } = useRequest(getChecksumInstance, {
    manual: true,
    onSuccess(data) {
      instanceList.value = data.results;
      if (instanceList.value.length > 0) {
        handleActive(instanceList.value[0]);
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

  const checkOverflow = () => {
    setTimeout(()=>{
      const elementList = document.querySelectorAll('.table-name');
      elementList.forEach(ele => {
        const { clientWidth } = ele;
        const rowKey = ele.getAttribute('row-key') as string;
        const textHeight = calcTextHeight(ele.innerHTML, clientWidth); // 计算实际文本高度，默认行高40
        isTextOverflow.value[rowKey] = textHeight > 400; // 400为最大高度，即最多展示10行
      })
    })
  }

  const handleActive = (data: UnwrapRef<typeof instanceList>[number]) => {
    activeKey.value = data.id;
    const dataList: IDataRow[] = [];
    const rows = convertDataRows(data.details);
    dataList.push(...rows);
    tableData.value = dataList;
    checkOverflow();
  };

  const convertDataRows = (details: Record<string, string[]>) =>
    Object.entries(details).reduce(
      (pre, [key, value]) => [
        ...pre,
        {
          db_name: key,
          table_name: value ? value.join(' , ') : '--',
        },
      ],
      [] as IDataRow[],
    );
</script>
<style lang="less">
  .inspection-instance-detail {
    display: flex;

    .wrapper-left {
      height: calc(100vh - 52px);
      padding: 16px;
      background-color: #f5f7fa;
      flex: 0 0 320px;

      .instance-list {
        height: calc(100% - 60px);
        margin-top: 12px;
        overflow-y: auto;
      }

      .instance-item {
        display: flex;
        height: 32px;
        padding: 0 12px;
        font-size: 12px;
        color: #63656e;
        cursor: pointer;
        background: #fff;
        border: 1px solid transparent;
        border-radius: 2px;
        align-items: center;
        transition: all 0.1s;

        & ~ .instance-item {
          margin-top: 8px;
          font-size: 12px;
        }

        &:hover {
          border-color: #3a84ff;
        }

        &.active {
          font-weight: bold;
          color: #3a84ff;
          border-color: #3a84ff;
        }
      }
    }

    .wrapper-right {
      padding: 24px;
      background: #fff;

      .header {
        display: flex;
        height: 36px;
        padding: 0 24px;
        font-size: 12px;
        font-weight: bold;
        color: #63656e;
        background: #f0f1f5;
        border-radius: 2px;
        align-items: center;
      }

      .bk-vxe-table td .vxe-cell .table-name {
        display: -webkit-box;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: pre-wrap;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 10;
      }
    }
  }
</style>
