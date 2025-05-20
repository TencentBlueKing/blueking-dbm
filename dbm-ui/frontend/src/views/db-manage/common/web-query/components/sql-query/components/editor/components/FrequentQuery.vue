<template>
  <div class="frequent-query-main">
    <div
      class="input-main"
      :class="{ 'is-no-input': !searchValue }">
      <BkInput
        v-model="searchValue"
        clearable
        @clear="handleSearch"
        @enter="handleSearch" />
    </div>
    <div class="query-list-wraper">
      <ScrollFaker theme="dark">
        <div class="query-list">
          <div
            v-for="(item, index) in recordList"
            :key="index"
            class="query-item"
            @click="() => handleChooseRecord(item.sql)">
            {{ item.name }}
          </div>
        </div>
      </ScrollFaker>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getCommonSqls } from '@services/source/systemSettings';

  import { DBTypes } from '@common/const';

  import { encodeRegexp } from '@utils';

  interface Props {
    dbType?: DBTypes;
    isProxy?: boolean;
  }

  type Emits = (e: 'chooseSql', sql: string) => void;

  type IDataRow = ServiceReturnType<typeof getCommonSqls>[number];

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
    isProxy: false,
  });

  const emits = defineEmits<Emits>();

  let recordListRaw: IDataRow[] = [];

  const searchValue = ref('');
  const recordList = shallowRef<IDataRow[]>([]);

  const { run: fetchCommonSqls } = useRequest(getCommonSqls, {
    manual: true,
    onSuccess(data) {
      recordListRaw = data;
      recordList.value = data;
    },
  });

  watch(
    () => [props.dbType, props.isProxy],
    () => {
      fetchCommonSqls({
        db_type: props.dbType,
        is_proxy: props.isProxy,
      });
    },
    {
      immediate: true,
    },
  );

  const handleChooseRecord = (sql: string) => {
    emits('chooseSql', sql);
  };

  const handleSearch = () => {
    if (searchValue.value) {
      const regex = new RegExp(encodeRegexp(searchValue.value));
      recordList.value = recordListRaw.filter((item) => regex.test(item.name));
      return;
    }

    recordList.value = recordListRaw;
  };
</script>
<style lang="less" scoped>
  .frequent-query-main {
    display: flex;
    width: 100%;
    height: 100%;
    padding: 12px;
    overflow: hidden;
    background-color: #282829;
    flex-direction: column;

    :deep(.bk-input--default) {
      border-color: #63656e;

      &.is-focused {
        border-color: #3a84ff;
      }
    }

    .input-main {
      &.is-no-input {
        :deep(.bk-input--text) {
          &::placeholder {
            color: #63656e;
          }
        }
      }

      :deep(.bk-input--text) {
        color: #c4c6cc;
        background-color: #232324;
      }

      :deep(.bk-input--suffix-icon) {
        background-color: #232324;
      }
    }

    .query-list-wraper {
      height: calc(100% - 60px);
      overflow: hidden;

      :deep(.query-list) {
        width: 100%;

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
  }
</style>
