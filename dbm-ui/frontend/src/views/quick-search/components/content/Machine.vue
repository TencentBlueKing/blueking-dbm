<template>
  <div>
    <DbCard
      class="search-result-machine search-result-card"
      mode="collapse"
      :title="t('主机')">
      <template #desc>
        <I18nT
          class="ml-8"
          keypath="共n条"
          style="color: #63656e"
          tag="span">
          <template #n>
            <strong>{{ count }}</strong>
          </template>
        </I18nT>
      </template>
      <DbTable
        ref="table"
        class="search-result-table mt-14"
        :data-source="dataSource"
        row-key="ip"
        @clear-search="handleClearSearch"
        @request-success="handleReqestSuccess">
        <TableColumn
          col-key="ip"
          fixed="left"
          title="IP"
          :width="150">
          <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
            <TextOverflowLayout>
              <BkButton
                text
                theme="primary"
                @click="handleGo(row)">
                <TextHighlight
                  high-light-color="#FF9C01"
                  :keyword="keyword"
                  :text="row.ip" />
              </BkButton>
              <template #append>
                <BkButton
                  class="ml-4"
                  text
                  theme="primary"
                  @click="handleCopy(row.ip)">
                  <DbIcon type="copy" />
                </BkButton>
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="poolDispaly"
          :title="t('所属池')"
          :width="130" />
        <TableColumn
          col-key="city"
          :title="t('地域')" />
        <TableColumn
          col-key="sub_zone"
          :title="t('园区')" />
        <TableColumn
          col-key="rack_id"
          :title="t('机架')" />
        <TableColumn
          col-key="os_name"
          show-overflow-tooltip
          :title="t('操作系统')"
          :width="180" />
        <TableColumn
          col-key="device_class"
          :title="t('机型')" />
        <TableColumn
          col-key="bk_cpu"
          :title="t('CPU (核)')"
          :width="160" />
        <TableColumn
          col-key="bkMemText"
          show-overflow-tooltip
          :title="t('内存（G）')"
          :width="120" />
        <TableColumn
          col-key="bk_disk"
          :title="t('磁盘 (G)')" />
      </DbTable>
    </DbCard>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { quickSearchResult } from '@services/source/quickSearch';

  import { useLocation } from '@hooks';

  import { batchSplitRegex } from '@common/regex';

  import DbIcon from '@components/db-icon/';
  import DbTable from '@components/db-table/IndexNew.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    formData: {
      bk_biz_ids: number[];
      db_types: string[];
      filter_type: string;
      resource_types: string[];
    };
    keyword: string;
  }

  interface Exposed {
    fetchData: () => void;
  }

  type Emits = (e: 'clear-search') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const location = useLocation();

  const tableRef = useTemplateRef('table');

  const count = ref(0);

  const fetchData = () => {
    if (props.formData.resource_types.length > 0 && !props.formData.resource_types.includes('machine')) {
      return;
    }
    tableRef.value?.fetchData();
  };

  // watch(
  //   () => props.keyword,
  //   () => {
  //     fetchData();
  //   },
  // );

  const dataSource = (params: ServiceParameters<typeof quickSearchResult>) => {
    return quickSearchResult({
      ...params,
      ...props.formData,
      keyword: props.keyword.replace(batchSplitRegex, ' '),
      resource_type: 'machine',
    });
  };

  const handleReqestSuccess = (data: ServiceReturnType<typeof quickSearchResult>) => {
    count.value = data.count;
  };

  const handleCopy = (content: string) => {
    execCopy(content, t('复制成功，共n条', { n: 1 }));
  };

  const handleGo = (data: FaultOrRecycleMachineModel) => {
    location({
      name: 'allHost',
      query: {
        ips: data.ip,
      },
    });
  };

  const handleClearSearch = () => {
    emits('clear-search');
  };

  // onMounted(() => {
  //   fetchData();
  // });

  onActivated(() => {
    fetchData();
  });

  defineExpose<Exposed>({
    fetchData,
  });
</script>

<style lang="less" scoped>
  @import './table-card.less';
</style>
