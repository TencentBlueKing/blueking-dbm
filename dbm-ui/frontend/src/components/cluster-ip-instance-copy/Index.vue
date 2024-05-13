<template>
  <BkDropdown
    class="ml-8"
    @hide="() => (isCopyDropdown = false)"
    @show="() => (isCopyDropdown = true)">
    <BkButton
      class="w-86"
      :class="{ active: isCopyDropdown }">
      {{ t('复制') }}
      <DbIcon
        class="ml-4"
        type="up-big" />
    </BkButton>
    <template #content>
      <BkDropdownMenu ext-cls="cluster-ip-instance-copy">
        <BkDropdownItem>
          <BkButton
            :disabled="dataList.length === 0"
            text
            @click="handleCopy(dataList)">
            {{ t('所有集群 IP') }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            :disabled="selected.length === 0"
            text
            @click="handleCopy(selected)">
            {{ t('已选集群 IP') }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            :disabled="abnormalDataList.length === 0"
            text
            @click="handleCopy(abnormalDataList)">
            {{ t('异常集群 IP') }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            :disabled="dataList.length === 0"
            text
            @click="handleCopy(dataList, true)">
            {{ t('所有集群实例') }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            :disabled="selected.length === 0"
            text
            @click="handleCopy(selected, true)">
            {{ t('已选集群实例') }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            :disabled="abnormalDataList.length === 0"
            text
            @click="handleCopy(abnormalDataList, true)">
            {{ t('异常集群实例') }}
          </BkButton>
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script
  setup
  lang="ts"
  generic="
    T extends
      | TendbhaModel
      | TendbsingleModel
      | SpiderModel
      | SqlServerHaModel
      | SqlServerSingleModel
      | RedisModel
      | MongodbModel
      | EsModel
      | HdfsModel
      | KafkaModel
      | PulsarModel
      | RiakModel
  ">
  import { useI18n } from 'vue-i18n';

  import EsModel from '@services/model/es/es';
  import HdfsModel from '@services/model/hdfs/hdfs';
  import KafkaModel from '@services/model/kafka/kafka';
  import MongodbModel from '@services/model/mongodb/mongodb';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import RedisModel from '@services/model/redis/redis';
  import RiakModel from '@services/model/riak/riak';
  import SpiderModel from '@services/model/spider/spider';
  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha-cluster';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single-cluster';

  import { useCopy } from '@hooks';

  interface Props {
    dataList: T[];
    selected: T[];
    roleList: string[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();

  const isCopyDropdown = ref(false);

  const abnormalDataList = computed(() => props.dataList.filter((dataItem) => dataItem.isAbnormal));

  const handleCopy = (dataList: T[], isInstance = false) => {
    const { roleList } = props;
    const copyList = dataList.reduce((prevList, tableItem) => {
      const resultList = roleList.reduce((resultPrev, roleItem) => {
        const roleInstanceList = tableItem[roleItem as keyof T] as {
          ip: string;
          port: number;
        }[];
        const result = roleInstanceList.map((instaneItem) =>
          isInstance ? `${instaneItem.ip}:${instaneItem.port}` : `${instaneItem.ip}`,
        );
        return [...resultPrev, ...result];
      }, [] as string[]);
      return [...prevList, ...resultList];
    }, [] as string[]);

    copy(copyList.join('\n'));
  };
</script>

<style lang="less" scoped>
  .cluster-ip-instance-copy {
    .bk-dropdown-item {
      padding: 0;

      .bk-button {
        height: 100%;
        padding: 0 16px;
      }
    }
  }
</style>
