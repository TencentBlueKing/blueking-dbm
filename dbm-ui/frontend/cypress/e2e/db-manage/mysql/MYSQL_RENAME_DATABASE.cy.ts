describe('Mysql DB 重命名 Test', () => {
  beforeEach(() => {
    // @ts-ignore
    cy.login();
    cy.viewport(1920, 1080);
    cy.intercept('get', '/apis/mysql/bizs/3/tendbha_resources/?bk_biz_id=3&limit=10&offset=0', {
      fixture: 'mysql/common/getTendbhaClusters.json',
    }).as('getTendbhaClusters');
    cy.intercept('post', '/apis/dbbase/check_cluster_databases/', (req) => {
      if (req.body.db_list[0] === 'test') {
        req.reply({
          fixture: 'mysql/MYSQL_RENAME_DATABASE/checkClusterDatabasesForTest.json',
        });
      } else {
        req.reply({
          fixture: 'mysql/MYSQL_RENAME_DATABASE/checkClusterDatabasesForHello.json',
        });
      }
    }).as('checkClusterDatabases');
    cy.intercept('post', '/apis/tickets/', {
      fixture: 'mysql/common/ticket.json',
    }).as('submitTicket');
  });

  it('Mysql DB 重命名', () => {
    cy.origin(Cypress.env('LOCAL_URL'), () => {
      Cypress.on('uncaught:exception', (err) => {
        if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
          return false;
        }
      });
      const url = '/3/db-manage/mysql/toolbox/MYSQL_RENAME_DATABASE';
      cy.visit(url);
      cy.get('.db-icon-batch-host-select').click();
      cy.wait('@getTendbhaClusters');
      cy.get('.vxe-body--row').not('is-offline').first().click();
      cy.get('[data-test-id="clusterSelectorPreviewItem"]').should('exist');
      cy.get('[data-test-id="clusterSelectorConfirmButton"]').click();
      cy.get('.bk-editable-tag-input').eq(0).click();
      cy.get('.bk-editable-tag-input').find('.tag-input').eq(0).type('test{enter}​');
      cy.wait('@checkClusterDatabases');
      cy.get('.bk-editable-tag-input').eq(1).click();
      cy.get('.bk-editable-tag-input').find('.tag-input').eq(1).type('hello{enter}​');
      cy.wait('@checkClusterDatabases');
      cy.get('textarea').type('前端自动化测试，请忽略此单据');
      cy.get('[data-test-id="submitTicket"]').click();
      cy.wait('@submitTicket');
      cy.get('.mysql-operation-success-page').should('contain', 'DB 重命名任务提交成功');
    });
  });
});
