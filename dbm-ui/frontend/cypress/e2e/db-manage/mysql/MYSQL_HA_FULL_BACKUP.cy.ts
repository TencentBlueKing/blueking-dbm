describe('MYSQL 全库备份 Test', () => {
  beforeEach(() => {
    cy.login();
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'common/listBizs.json',
    }).as('listBizs');
    cy.intercept('get', '/apis/mysql/bizs/3/tendbha_resources/?bk_biz_id=3&limit=10&offset=0', {
      fixture: 'mysql/common/getTendbhaClusters.json',
    }).as('getTendbhaClusters');
    cy.intercept('post', '/apis/tickets/', {
      fixture: 'common/ticket.json',
    }).as('submitTicket');
  });

  it('MYSQL 全库备份', () => {
    cy.on('uncaught:exception', (err) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    cy.viewport(1920, 1080);
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_HA_FULL_BACKUP`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('.db-icon-batch-host-select').click();
    cy.wait('@getTendbhaClusters');
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="span_clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="button_clusterSelectorConfirm"]').click();
    cy.get('[data-test-id="input_ticketRemark"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="button_submitTicket"]').click();
    cy.wait('@submitTicket');
    cy.get('.toolbox-result-success-page').should('contain', '全库备份任务提交成功');
  });
});
