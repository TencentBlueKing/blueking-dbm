<template>
  <BkDialog
    v-model:is-show="moduleValue"
    class="todo-batch-delete-dialog"
    quick-close
    :title="t('批量下架')"
    :width="500">
    <div class="dialog-content">
      <BkAlert
        class="mb-8"
        theme="info"
        :title="
          isSplitOrder
            ? t('已选集群将按所属业务和架构类型拆分为不同的下架单据')
            : t('已选 m 个集群，将创建 n 个下架单据', { m: selected.length, n: ticketList.length })
        " />
      <BkCard
        v-for="(ticketItem, index) in ticketList"
        :key="index"
        class="ticket-card mt-8"
        is-collapse>
        <template #header>
          <div class="card-header-wrapper">
            <div v-if="bizTypeDType.includes(props.dbType)">
              【
              <span class="head-name">{{ getBizInfoById(ticketItem[0].bk_biz_id)?.name }}</span>
              -
              <span class="head-type">{{ ticketItem[0].clusterTypesDisplay }}</span>
              】-
              <I18nT
                keypath="共 n 个"
                tag="span">
                <span class="head-count">{{ ticketItem.length }}</span>
              </I18nT>
            </div>
            <div v-else>
              【
              <span class="head-name">{{ getBizInfoById(ticketItem[0].bk_biz_id)?.name }}</span>
              】-
              <I18nT
                keypath="共 n 个"
                tag="span">
                <span class="head-count">{{ ticketItem.length }}</span>
              </I18nT>
            </div>
          </div>
        </template>
        <div class="card-content-wrapper">
          <div
            v-for="cardItem in ticketItem"
            :key="cardItem.id"
            class="card-item">
            {{ cardItem.immute_domain }}
          </div>
        </div>
      </BkCard>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('确认提交') }}
      </BkButton>
      <BkButton
        :disabled="isLoading"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import _, { type Dictionary } from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketClusterDisableTodoModel from '@services/model/ticket-cluster-disable-todo/TicketClusterDisableTodo';
  import { createTicketBatch } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import { getBusinessHref, messageError } from '@utils';

  interface Props {
    dbType: DBTypes;
    selected: TicketClusterDisableTodoModel[];
  }

  type Emits = (e: 'suceess') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const moduleValue = defineModel<boolean>();

  const router = useRouter();
  const { locale, t } = useI18n();
  const { getBizInfoById } = useGlobalBizs();
  const bizTypeDType = [DBTypes.MYSQL, DBTypes.REDIS];

  const isLoading = ref(false);

  const isSplitOrder = computed(
    () => bizTypeDType.includes(props.dbType) || _.uniqBy(props.selected, 'bk_biz_id').length > 1,
  );

  const ticketList = computed(() => {
    let results: Dictionary<TicketClusterDisableTodoModel[]>;

    // 需要按架构类型拆的（MySQL、Redis）：按 业务 × 架构类型 拆
    // 不需要按架构类型拆的（MongoDB、SQLServer、TenDBCluster）：仅按 业务 拆
    if (bizTypeDType.includes(props.dbType)) {
      results = _.flow([
        (items) => _.orderBy(items, ['bk_biz_id', 'cluster_type'], ['asc', 'asc']),
        (items) => _.groupBy(items, (item) => `${item.bk_biz_id}-${item.cluster_type}`),
      ])(props.selected);
    } else {
      results = _.flow([
        (items) => _.orderBy(items, ['bk_biz_id'], ['asc']),
        (items) => _.groupBy(items, (item) => item.bk_biz_id),
      ])(props.selected);
    }

    return Object.values(results);
  });

  const handleSubmit = () => {
    const ticketTypeMap: Record<string, TicketTypes> = {
      [ClusterTypes.MONGODB]: TicketTypes.MONGODB_DESTROY,
      [ClusterTypes.REDIS_INSTANCE]: TicketTypes.REDIS_INSTANCE_DESTROY,
      [ClusterTypes.SQLSERVER]: TicketTypes.SQLSERVER_DESTROY,
      [ClusterTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_DESTROY,
      [ClusterTypes.TENDBHA]: TicketTypes.MYSQL_HA_DESTROY,
      [ClusterTypes.TENDBSINGLE]: TicketTypes.MYSQL_SINGLE_DESTROY,
    };

    const tickets = ticketList.value.map((ticketItem) => ({
      bk_biz_id: ticketItem[0].bk_biz_id,
      details: {
        cluster_ids: ticketItem.map((item) => item.id),
      },
      remark: '',
      ticket_type: ticketTypeMap[ticketItem[0].cluster_type],
    }));

    doRequest(tickets);
  };

  const getTicketRoute = (res: ServiceReturnType<typeof createTicketBatch>) => {
    if (res.length > 1) {
      const route = router.resolve({
        name: 'SelfServiceMyTickets',
        query: {
          ids: res.map((item) => item.id).join(','),
        },
      });
      return route.href;
    }

    const route = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: res[0].id,
      },
    });
    return getBusinessHref(route.href, res[0].bk_biz_id);
  };

  const doRequest = async (tickets: ServiceParameters<typeof createTicketBatch>['tickets']) => {
    try {
      isLoading.value = true;
      const res = await createTicketBatch({ tickets });

      Message({
        delay: 6000,
        dismissable: false,
        message: h('div', { style: 'width: 100%; display: flex; justify-content: space-between;' }, [
          h('span', {}, t('单据提交成功！已成功提交 n 个下架单据', { n: res.length })),
          h(
            'a',
            {
              href: getTicketRoute(res),
              target: '_blank',
            },
            t('查看详情'),
          ),
        ]),
        theme: 'success',
      });

      moduleValue.value = false;
      emits('suceess');
    } catch (e: any) {
      const { code, data, message } = e;
      const duplicateCode = 8704005;
      // 批量提单暂时不会校验单据互斥
      if (code === duplicateCode) {
        const id = data.duplicate_ticket_id;

        InfoBox({
          cancelText: t('取消提单'),
          confirmText: t('继续提单'),
          content: () => {
            const route = router.resolve({
              name: 'bizTicketManage',
              params: {
                ticketId: id,
              },
            });

            if (locale.value === 'en') {
              return (
                <span>
                  The system has detected that a similar ticket has already been submitted
                  <a
                    href={route.href}
                    target='_blank'>
                    {' '}
                    ticket[{id}]{' '}
                  </a>
                  with the same target cluster, continue?
                </span>
              );
            }

            return (
              <span>
                系统检测到已提交过包含相同集群的同类
                <a
                  href={route.href}
                  target='_blank'>
                  单据[{id}]
                </a>
                ，是否继续？
              </span>
            );
          },
          onConfirm: async () => {
            try {
              const ignoreTickets = tickets.map((ticket) => ({
                ...ticket,
                ignore_duplication: true,
              }));
              await doRequest(ignoreTickets);
            } catch (e: any) {
              messageError(e?.message);
            }
          },
          title: t('是否继续提交单据'),
        });
      } else {
        messageError(message);
      }
    } finally {
      isLoading.value = false;
    }
  };

  const handleCancel = () => {
    moduleValue.value = false;
  };
</script>

<style lang="less">
  .todo-batch-delete-dialog {
    .dialog-content {
      max-height: 500px;
      overflow: auto;

      .ticket-card {
        .card-header-wrapper {
          font-size: 12px;

          .head-name {
            color: #3a84ff;
          }

          .head-type {
            color: #3a84ff;
          }

          .head-count {
            color: #3a84ff;
          }
        }

        .bk-card-body {
          background-color: #f5f7fa;
        }

        .card-content-wrapper {
          padding: 12px 0;

          .card-item {
            padding: 10px 12px;
            font-size: 12px;
            color: #63656e;
            background: #fff;
            border: 1px solid #e6e8ed;
            border-radius: 4px;
          }
        }
      }
    }
  }
</style>
