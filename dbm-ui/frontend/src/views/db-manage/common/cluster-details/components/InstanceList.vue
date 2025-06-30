<template>
  <div class="cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <BkDropdown
        :popover-options="{
          clickContentAutoHide: true,
          hideIgnoreReference: true,
        }">
        <template #default="{ popoverShow }">
          <BkButton style="width: 105px">
            {{ t('复制实例') }}
            <DbIcon
              :class="{ 'is-show': popoverShow }"
              type="up-big" />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="selectionList.length < 1"
                text
                @click="handleCopySelectedInstance">
                {{ t('已选实例') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleCopyAbnormalInstance">
                {{ t('异常实例') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleCopyAllInstance">
                {{ t('全部实例') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkDropdown
        class="mr-20"
        :popover-options="{
          clickContentAutoHide: true,
          hideIgnoreReference: true,
        }">
        <template #default="{ popoverShow }">
          <BkButton
            class="ml-8"
            style="width: 105px">
            {{ t('复制 IP') }}
            <DbIcon
              :class="{ 'is-show': popoverShow }"
              type="up-big" />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="selectionList.length < 1"
                text
                @click="handleCopySelectedIp">
                {{ t('已选 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleCopyAbnormalIp">
                {{ t('异常 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleAllIp">
                {{ t('全部 IP') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DbSearchSelect
        :data="searchSelectData"
        :model-value="searchSelectValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="flex: 1; max-width: 560px; margin-left: auto"
        unique-select
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="dbTable"
      :data-source="dataSource"
      selectable
      @selection="handleSelection">
      <BkTableColumn
        field="instance_address"
        fixed="left"
        :min-width="250"
        :title="t('实例')">
        <template #default="{ data }: { data: IColumnData }">
          {{ data.instance_address || '--' }}
          <BkTag
            v-if="standBdyTagMap[data.instance_address]"
            class="cluster-specific-flag ml-4"
            size="small">
            Standby
          </BkTag>
          <BkTag
            v-if="primaryTagMap[data.instance_address]"
            class="cluster-specific-flag ml-4"
            size="small">
            Primary
          </BkTag>
        </template>
      </BkTableColumn>
      <InstanceListFieldColumn />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { ClusterListNode } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { ClusterInstStatusKeys } from '@common/const';

  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';

  import { URL_INSTANCE_MEMO_KEY } from '../constants';
  import InstanceListFieldColumn from '../InstanceListFieldColumn.vue';
  import { getSearchSelectValue } from '../utils/index';

  interface Props {
    clusterId: number;
    clusterRoleNodeGroup: Record<
      string,
      ({
        displayInstance?: string;
        isPrimary?: boolean;
        isStandBy?: boolean;
      } & ClusterListNode)[]
    >;
    clusterType: Parameters<typeof useClusterInstanceList>[0];
  }

  type IColumnData = ServiceReturnType<ReturnType<typeof useClusterInstanceList>>['results'][number];
  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const urlPaylaod = JSON.parse(decodeURIComponent(String(route.query[URL_INSTANCE_MEMO_KEY] || '{}')));

  const requestHandler = useClusterInstanceList(props.clusterType);
  const { getSearchParams } = useUrlSearch();

  const searchSelectData = [
    {
      id: 'instance',
      name: t('实例'),
    },
    {
      id: 'ip',
      name: 'IP',
    },
    {
      children: [
        {
          id: 'restoring',
          name: t('恢复中'),
        },
        {
          id: 'running',
          name: t('运行中'),
        },
        {
          id: 'unavailable',
          name: t('不可用'),
        },
        {
          id: 'upgrading',
          name: t('升级中'),
        },
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      id: 'role',
      name: t('部署角色'),
    },
    {
      id: 'version',
      name: t('版本'),
    },
  ];

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      ...params,
      cluster_id: props.clusterId,
    });

  const dbTable = useTemplateRef('dbTable');
  const primaryTagMap = shallowRef<Record<string, boolean>>({});
  const standBdyTagMap = shallowRef<Record<string, boolean>>({});
  const searchSelectValue = shallowRef<ReturnType<typeof getSearchSelectValue>>([]);
  const selectionList = shallowRef<IColumnData[]>([]);

  watch(
    () => props.clusterRoleNodeGroup,
    () => {
      const latestPrimaryTagMap: Record<string, boolean> = {};
      const latestStandBdyTagMap: Record<string, boolean> = {};
      Object.entries(props.clusterRoleNodeGroup).forEach(([, nodes]) => {
        nodes.forEach((node) => {
          if (node.isPrimary) {
            latestPrimaryTagMap[node.instance] = true;
          }
          if (node.isStandBy) {
            latestStandBdyTagMap[node.instance] = true;
          }
        });
      });
      primaryTagMap.value = latestPrimaryTagMap;
      standBdyTagMap.value = latestStandBdyTagMap;
    },
    {
      immediate: true,
    },
  );

  const copyFieldData = (data: IColumnData[], field: 'ip' | 'instance_address') => {
    const result = _.uniq(data.map((item) => item[field]) || []);

    if (result.length < 1) {
      messageWarn(t('没有可复制数据'));
      return;
    }
    execCopy(
      result.join('\n'),
      t('复制成功，共n条', {
        n: result.length,
      }),
    );
  };

  const handleCopySelectedInstance = () => {
    copyFieldData(selectionList.value, 'instance_address');
  };

  const handleCopyAbnormalInstance = () => {
    copyFieldData(
      _.filter(dbTable.value?.getData<IColumnData>() || [], (item) => item.status !== ClusterInstStatusKeys.RUNNING),
      'instance_address',
    );
  };

  const handleCopyAllInstance = () => {
    copyFieldData(dbTable.value?.getData<IColumnData>() || [], 'instance_address');
  };

  const handleCopySelectedIp = () => {
    copyFieldData(selectionList.value, 'ip');
  };

  const handleCopyAbnormalIp = () => {
    copyFieldData(
      _.filter(dbTable.value?.getData<IColumnData>() || [], (item) => item.status !== ClusterInstStatusKeys.RUNNING),
      'ip',
    );
  };

  const handleAllIp = () => {
    copyFieldData(dbTable.value?.getData<IColumnData>() || [], 'ip');
  };

  const handleSearchValueChange = _.debounce((payload: any) => {
    const serachParams = getSearchSelectorParams(payload);
    dbTable.value?.fetchData(serachParams);
    router.replace({
      query: {
        ...getSearchParams(),
        [URL_INSTANCE_MEMO_KEY]: encodeURIComponent(JSON.stringify(serachParams)),
      },
    });
  }, 100);

  const handleSelection = (_: any, list: IColumnData[]) => {
    selectionList.value = list;
  };

  onMounted(() => {
    searchSelectValue.value = getSearchSelectValue(searchSelectData, urlPaylaod);
  });
</script>
<style lang="less">
  .cluster-detail-instance-list-box {
    height: 100%;
    padding: 18px 0;

    .action-box {
      display: flex;
    }

    .is-show {
      transform: rotateZ(180deg);
      transition: all 0.15s;
    }
  }
</style>
