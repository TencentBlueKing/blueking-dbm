<template>
  <div class="my-collect-main">
    <BkInput
      v-model="searchValue"
      class="input-main"
      :class="{ 'is-no-input': !searchValue }"
      clearable
      @clear="handleSearch"
      @enter="handleSearch" />
    <BkTable
      border="none"
      class="table-main"
      :data="tableData"
      header-row-class-name="my-collect-table-header-row"
      height="100%"
      row-class-name="my-collect-table-row-class"
      :row-config="{
        keyField: 'name',
      }"
      :sort-config="{
        sortMethod: handleSort,
      }"
      @cell-click="handleCellClick">
      <BkTableColumn
        field="name"
        :label="t('名称')"
        :min-width="200"
        sortable>
        <template #default="{ data, rowIndex }: { data: IDataRow; rowIndex: number }">
          <div class="my-collect-name-main">
            <div class="icon-main">
              <DbIcon
                v-if="data.is_top"
                class="favorite-item"
                type="pinned"
                @click="() => handleCancelPinned(rowIndex)" />
              <DbIcon
                v-else
                class="favorite-item unfavorite-icon"
                type="dingzhu"
                @click="() => handleClickPin(rowIndex)" />
            </div>
            <div class="name-display">{{ data.name }}</div>
          </div>
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('操作')"
        :width="120">
        <template #default="{ rowIndex }: { rowIndex: number }">
          <BkPopConfirm
            :confirm-config="{
              theme: 'danger',
            }"
            :confirm-text="t('删除')"
            :content="t('删除操作无法撤回，请谨慎操作！')"
            :title="t('确认删除该收藏？')"
            trigger="click"
            width="280"
            @confirm="() => handleDelete(rowIndex)">
            <BkButton
              class="mr-8"
              text
              theme="primary">
              {{ t('删除') }}
            </BkButton>
          </BkPopConfirm>
          <BkPopConfirm
            :title="t('重命名')"
            trigger="click"
            width="340"
            @confirm="() => handleClickRename(rowIndex)">
            <template #content>
              <div class="my-collection-rename-main">
                <div class="collect-title">
                  {{ t('条件名称') }}
                </div>
                <AutoFocusInput
                  v-model="sqlName"
                  class="mt-6 mb-18" />
              </div>
            </template>
            <BkButton
              text
              theme="primary">
              {{ t('重命名') }}
            </BkButton>
          </BkPopConfirm>
        </template>
      </BkTableColumn>
    </BkTable>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { upsertProfile } from '@services/source/profile';

  import { DBTypes } from '@common/const';

  import { messageError } from '@utils';

  import type { SqlProfile } from '../Index.vue';

  import AutoFocusInput from './AutoFocusInput.vue';

  interface Props {
    dbType?: DBTypes;
    sqlProfile?: SqlProfile;
  }

  interface Emits {
    (e: 'change'): void;
    (e: 'chooseSql', sql: string): void;
  }

  type IDataRow = SqlProfile[string][number];

  const props = withDefaults(defineProps<Props>(), {
    dbType: DBTypes.MYSQL,
    sqlProfile: undefined,
  });

  const emits = defineEmits<Emits>();

  let tableDataRaw: IDataRow[] = [];

  const { t } = useI18n();

  const tableData = ref<IDataRow[]>([]);
  const searchValue = ref('');
  const sqlName = ref('');

  const { run: updateProfile } = useRequest(upsertProfile, {
    manual: true,
    onSuccess() {
      emits('change');
    },
  });

  watch(
    () => props.sqlProfile,
    () => {
      if (props.sqlProfile) {
        tableDataRaw = props.sqlProfile[props.dbType];
        tableData.value = _.cloneDeep(tableDataRaw);
      }
    },
    {
      immediate: true,
    },
  );

  const handleCellClick = (data: { row: IDataRow }) => {
    emits('chooseSql', data.row.sql);
  };

  const handleSearch = () => {
    if (searchValue.value) {
      const regex = new RegExp(searchValue.value);
      tableData.value = tableDataRaw.filter((item) => regex.test(item.name));
      return;
    }

    tableData.value = _.cloneDeep(tableDataRaw);
  };

  const handleCancelPinned = (index: number) => {
    const item = _.cloneDeep(tableData.value[index]);
    item.is_top = false;
    tableData.value.splice(index, 1);
    const notPinnedIndex = tableData.value.findIndex((item) => !item.is_top);
    tableData.value.splice(notPinnedIndex, 0, item);
    handleUpdateProfile(tableData.value);
  };

  const handleClickPin = (index: number) => {
    const item = _.cloneDeep(tableData.value[index]);
    item.is_top = true;
    tableData.value.splice(index, 1);
    tableData.value.unshift(item);
    handleUpdateProfile(tableData.value);
  };

  const handleClickRename = (index: number) => {
    if (!sqlName.value) {
      messageError(t('收藏名称不能为空'));
      return;
    }

    const nameList = props.sqlProfile![props.dbType].map((item) => item.name);
    if (nameList.includes(sqlName.value)) {
      sqlName.value = '';
      messageError(t('收藏名称已存在'));
      return;
    }

    tableData.value[index].name = sqlName.value;
    handleUpdateProfile(tableData.value);
  };

  const handleSort = (data: {
    data: IDataRow[];
    sortList: {
      field: string;
      order: 'desc' | 'asc';
    }[];
  }) => {
    const { order } = data.sortList[0];
    return data.data.sort((a, b) => (order === 'desc' ? b.name.localeCompare(a.name) : a.name.localeCompare(b.name)));
  };

  const handleUpdateProfile = (data: IDataRow[]) => {
    updateProfile({
      label: 'SQL',
      values: {
        ...props.sqlProfile,
        [props.dbType]: data,
      },
    });
  };

  const handleDelete = (index: number) => {
    tableData.value.splice(index, 1);
    handleUpdateProfile(tableData.value);
  };
</script>
<style lang="less" scoped>
  .my-collect-main {
    display: flex;
    width: 100%;
    height: calc(100% - 40px);
    padding: 12px;
    background-color: #282829;
    flex-direction: column;

    :deep(.bk-input--default) {
      border-color: #6e6365;

      &.is-focused {
        border-color: #3a84ff;
      }
    }

    .input-main {
      margin-bottom: 12px;

      &.is-no-input {
        :deep(.bk-input--text) {
          &::placeholder {
            color: #63656e;
          }
        }
      }

      :deep(.bk-input--suffix-icon) {
        background-color: #232324;
      }

      :deep(.bk-input--text) {
        color: #c4c6cc;
        background-color: #232324;
      }
    }

    .table-main {
      height: calc(100% - 48px);

      :deep(.vxe-table--body-wrapper) {
        background-color: #282829 !important;
      }

      :deep(.vxe-table--scroll-y-virtual) {
        visibility: visible;

        &::before {
          border: none;
        }

        .vxe-table--scroll-y-top-corner {
          background-color: #282829;
          border-bottom: none;
        }

        .vxe-table--scroll-y-handle {
          background-color: #282829;

          &:hover {
            &::-webkit-scrollbar {
              width: 10px;
              height: 10px;
              border-radius: 5px;
              opacity: 68%;
            }
          }

          &::-webkit-scrollbar {
            width: 6px;
            height: 6px;
            background: #f0f5ff;
            border-radius: 3px;
            opacity: 40%;

            &:hover {
              width: 10px;
              height: 10px;
              border-radius: 5px;
              opacity: 68%;
            }
          }

          &::-webkit-scrollbar-track {
            background: #282829;
          }
        }
      }
    }
  }
</style>
<style lang="less">
  .my-collect-table-header-row {
    .vxe-header--column {
      background-color: #3d3d3d;
      background-image: none !important;

      &:hover {
        background-color: #474747 !important;
      }
    }

    .vxe-cell--title {
      color: #eaebf0;
    }
  }

  .my-collect-table-row-class {
    cursor: pointer;
    background-color: #282829;

    &:hover {
      background-color: #333 !important;

      .my-collect-name-main {
        .icon-main {
          .unfavorite-icon {
            display: block;
          }
        }
      }
    }

    .vxe-body--column {
      border-bottom: solid 1px #3d3d3d;

      .vxe-cell {
        color: #c4c6cc;
      }
    }
  }

  .my-collect-name-main {
    position: relative;
    display: flex;
    width: 100%;
    align-items: center;

    .icon-main {
      position: absolute;
      left: -15px;
      display: flex;
      width: 10px;
      align-items: center;

      .favorite-item {
        color: #979ba5;
      }

      .unfavorite-icon {
        display: none;
      }
    }

    .unfavorite-icon {
      display: none;
    }

    .name-display {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }
  }

  .my-collection-rename-main {
    .collect-title {
      position: relative;

      &::after {
        position: absolute;
        top: 2px;
        left: 54px;
        color: #ea3636;
        content: '*';
      }
    }
  }
</style>
