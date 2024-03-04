<template>
  <BkDialog
    :is-show="isShow"
    :title="t('添加授权规则')"
    :width="1100">
    <div class="openarea-create-permission-rule">
      <div class="mb-16">
        <BkInput style="width: 520px" />
      </div>
      <DbTable
        ref="tableRef"
        :cell-class="cellClassCallback"
        :columns="columns"
        :container-height="600"
        :data-source="getPermissionRules"
        settings />
    </div>
    <template #footer>
      <div style="display: flex">
        <I18nT
          v-if="checkedCount"
          keypath="已选n个"
          tag="div">
          <span
            class="number"
            style="color: #2dcb56">
            {{ checkedCount }}
          </span>
        </I18nT>
        <BkButton
          style="margin-left: auto"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getPermissionRules } from '@services/permission';

  type IColumnData = ServiceReturnType<typeof getPermissionRules>['results'][0]

  interface Props {
    clusterId: number,
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
    required: true,
  });
  const modleValue = defineModel<number[]>({
    default: [],
  });

  const { t } = useI18n();

  const tableRef = ref();
  const rowFlodMap = ref<Record<string, boolean>>({});
  const ruleCheckedMap = ref<Record<number, boolean>>({});

  const checkedCount = computed(() => Object.keys(ruleCheckedMap.value).length);

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: { data: IColumnData }) => (
        <div class="account-box">
          {
            data.rules.length > 1
              && <db-icon
                  type="down-shape"
                  class={{
                    'flod-flag': true,
                    'is-flod': rowFlodMap.value[data.account.user],
                  }}
                  onClick={() => handleToogleExpand(data.account.user)} />
          }
          { data.account.user }
        </div>
      ),
    },
    {
      label: t('访问DB'),
      width: 300,
      field: 'access-db',
      showOverflowTooltip: true,
      sort: true,
      render: ({ data }: { data: IColumnData }) => {
        if (data.rules.length === 0) {
          return (
            <div class="inner-row">
              <bk-checkbox class="mr-8" disabled />
              <span>{t('暂无规则，')}</span>
              <router-link
                to={{
                    name: 'PermissionRules',
                }}
                target="_blank">
                {t('去创建')}
              </router-link>
            </div>
          );
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;

        return renderRules.map(item => (
          <div class="inner-row">
            <bk-checkbox
              class="mr-8"
              modleValue={ruleCheckedMap.value[item.rule_id]}
              onChange={(value: boolean) => handleDbChange(value, item.rule_id)} />
            <bk-tag>
              {item.access_db}
            </bk-tag>
          </div>
        ));
      },
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: true,
      sort: true,
      render: ({ data }: { data: IColumnData }) => {
        if (data.rules.length === 0) {
          return <div class="inner-row">--</div>;
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row">
            {item.privilege}
          </div>
        ));
      },
    },
  ];

  const cellClassCallback = (data: any) => (data.field ? `cell-${data.field}` : '');

  const handleToogleExpand = (user: string) => {
    if (rowFlodMap.value[user]) {
      delete rowFlodMap.value[user];
    } else {
      rowFlodMap.value[user] = true;
    }
  };

  const handleDbChange = (checked: boolean, ruleId: number) => {
    if (checked) {
      ruleCheckedMap.value[ruleId] = true;
    } else {
      delete ruleCheckedMap.value[ruleId];
    }
  };

  watch(isShow, () => {
    if (!isShow.value) {
      return;
    }
    nextTick(() => {
      tableRef.value.fetchData({
        cluster_id: props.clusterId,
      }, {
        account_type: 'mysql',
      });
    });
  });

  watch(modleValue, () => {
    if (isShow.value) {
      ruleCheckedMap.value = modleValue.value.reduce((result, id) => Object.assign(result, {
        [id]: true,
      }), {});
    }
  });

  const handleSubmit = () => {
    modleValue.value = Object.keys(ruleCheckedMap.value).map(item => Number(item));
    isShow.value = false;
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .openarea-create-permission-rule {
    .account-box {
      .flod-flag {
        display: inline-block;
        margin-right: 4px;
        cursor: pointer;
        transition: all 0.1s;

        &.is-flod {
          transform: rotateZ(-90deg);
        }
      }
    }

    .cell-privilege {
      .cell {
        padding: 0 !important;
        margin-left: -16px;

        .inner-row {
          padding-left: 32px !important;
        }
      }
    }

    .inner-row {
      display: flex;
      height: 40px;
      align-items: center;

      & ~ .inner-row {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
