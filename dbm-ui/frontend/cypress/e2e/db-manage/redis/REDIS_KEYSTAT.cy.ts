describe('REDIS 内存分析 Test', () => {
  beforeEach(() => {
    cy.login();
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'common/listBizs.json',
    }).as('listBizs');
    cy.intercept(
      'get',
      '/apis/redis/bizs/5/redis_resources/list_instances/?bk_biz_id=5&extra=1&limit=10&offset=0&role=redis_master&cluster_type=TwemproxyRedisInstance%2CRedisCluster%2CRedisInstance',
      {
        fixture: 'redis/REDIS_KEYSTAT/getRedisInstances.json',
      },
    ).as('getRedisInstances');
    cy.intercept('post', '/apis/tickets/', {
      fixture: 'common/ticket.json',
    }).as('submitTicket');
  });

  it('REDIS 内存分析', () => {
    cy.on('uncaught:exception', (err) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    cy.viewport(1920, 1080);
    const url = `${Cypress.env('LOCAL_URL')}/5/db-manage/redis/toolbox/REDIS_KEYSTAT`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('.db-icon-batch-host-select').click();
    cy.wait('@getRedisInstances');
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="span_instanceSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="button_instanceSelectorConfirm"]').click();
    cy.get('[data-test-id="input_ticketRemark"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="button_submitTicket"]').click();
    cy.wait('@submitTicket');
    cy.get('.toolbox-result-success-page').should('contain', '内存分析任务提交成功');
  });
});
