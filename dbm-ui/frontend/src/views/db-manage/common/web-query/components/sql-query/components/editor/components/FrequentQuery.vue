<template>
  <div class="frequent-query-main">
    <BkInput
      v-model="searchValue"
      class="input-main"
      clearable
      @clear="handleSearch"
      @enter="handleSearch" />
    <div class="query-list">
      <div
        v-for="(item, index) in recordList"
        :key="index"
        class="query-item"
        @click="() => handleChooseRecord(item.sql)">
        {{ item.name }}
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useRequest } from 'vue-request';

  import { getCommonSqls } from '@services/source/systemSettings';

  import { DBTypes } from '@common/const';

  interface Props {
    dbType?: DBTypes;
  }

  type Emits = (e: 'chooseSql', sql: string) => void;

  type IDataRow = ServiceReturnType<typeof getCommonSqls>[number];

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
  });

  const emits = defineEmits<Emits>();

  let recordListRaw: IDataRow[] = [];

  const searchValue = ref('');
  const recordList = ref<IDataRow[]>([]);

  useRequest(getCommonSqls, {
    defaultParams: [
      {
        db_type: props.dbType,
      },
    ],
    onSuccess(data) {
      recordListRaw = data;
      recordList.value = data;
    },
  });

  const handleChooseRecord = (sql: string) => {
    emits('chooseSql', sql);
  };

  const handleSearch = () => {
    if (searchValue.value) {
      const regex = new RegExp(searchValue.value);
      recordList.value = recordListRaw.filter((item) => regex.test(item.name));
      return;
    }

    recordList.value = _.cloneDeep(recordListRaw);
  };
</script>
<style lang="less" scoped>
  .frequent-query-main {
    display: flex;
    width: 100%;
    height: 100%;
    padding: 12px;
    overflow-y: auto;
    background-color: #282829;
    flex-direction: column;

    :deep(.bk-input--default) {
      border-color: #63656e;

      .bk-input--text {
        background-color: #232324;
        border-color: #63656e;
      }
    }

    .input-main {
      :deep(.bk-input--suffix-icon) {
        background-color: #232324;
      }

      :deep(.bk-input--text) {
        color: #c4c6cc;
      }
    }

    .query-list {
      width: 100%;
      margin-top: 12px;
      overflow-y: auto;
      flex: 1;

      .query-item {
        width: 100%;
        height: 32px;
        padding: 0 12px;
        overflow: hidden;
        font-size: 12px;
        color: #c4c6cc;
        text-overflow: ellipsis;
        white-space: nowrap;
        cursor: pointer;
        border-bottom: solid 1px #3d3d3d;

        &:hover {
          background-color: #333;
        }
      }
    }
  }
</style>
