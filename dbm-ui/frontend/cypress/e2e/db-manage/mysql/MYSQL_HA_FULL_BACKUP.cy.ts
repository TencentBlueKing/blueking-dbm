describe('MYSQL 全库备份 Test', () => {
  beforeEach(() => {
    // @ts-ignore
    cy.login();
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'mysql/common/listBizs.json',
    }).as('listBizs');
    cy.intercept('get', '/apis/mysql/bizs/3/tendbha_resources/?bk_biz_id=3&limit=10&offset=0', {
      fixture: 'mysql/common/getTendbhaClusters.json',
    }).as('getTendbhaClusters');
    cy.intercept('post', '/apis/tickets/', {
      fixture: 'mysql/common/ticket.json',
    }).as('submitTicket');
  });

  it('MYSQL 全库备份', () => {
    cy.viewport(1920, 1080);
    cy.origin(Cypress.env('LOCAL_URL'), () => {
      Cypress.on('uncaught:exception', (err, runnable) => {
        if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
          return false;
        }
      });
      const url = '/3/db-manage/mysql/toolbox/MYSQL_HA_FULL_BACKUP';
      cy.visit(url);
      cy.wait('@listBizs');
      cy.get('.db-icon-batch-host-select').click();
      cy.wait('@getTendbhaClusters');
      cy.get('.vxe-body--row').not('is-offline').first().click();
      cy.get('[data-test-id="clusterSelectorPreviewItem"]').should('exist');
      cy.get('[data-test-id="clusterSelectorConfirmButton"]').click();
      cy.get('textarea').type('前端自动化测试，请忽略此单据');
      cy.get('[data-test-id="submitTicket"]').click();
      cy.wait('@submitTicket');
      cy.get('.mysql-operation-success-page').should('contain', '全库备份任务提交成功');
    });
  });
});
