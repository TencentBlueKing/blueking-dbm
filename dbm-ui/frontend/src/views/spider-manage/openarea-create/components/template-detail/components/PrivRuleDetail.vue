<template>
  <div class="openarea-template-detail-priv-rule">
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
</template>
<script setup lang="tsx">
  import {
    onMounted,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getPermissionRules } from '@services/permission';

  type IColumnData = ServiceReturnType<typeof getPermissionRules>['results'][0]

  interface Props {
    clusterId: number,
    ruleIdList: number[]
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref();

  const rowFlodMap = ref<Record<string, boolean>>({});

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: { data: IColumnData }) => (
        <div class="account-box">
            <db-icon
              type="down-shape"
              class={{
                'flod-flag': true,
                'is-flod': rowFlodMap.value[data.account.user],
              }}
              style={{
                opacity: data.rules.length < 2 ? 0 : 1,
              }}
              onClick={() => handleToogleExpand(data.account.user)} />
            <bk-button
              text
              theme="primary">
              { data.account.user }
            </bk-button>
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
        if (data.rules.length < 1) {
          return '--';
        }

        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;

        return renderRules.map(item => (
          <div class="inner-row">
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

  onMounted(() => {
    tableRef.value.fetchData({
      cluster_id: props.clusterId,
      rule_ids: props.ruleIdList.join(','),
      account_type: 'tendbcluster',
    });
  });
</script>
<style lang="less">
  .openarea-template-detail-priv-rule {
    min-height: 624px;
    padding-bottom: 24px;

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
