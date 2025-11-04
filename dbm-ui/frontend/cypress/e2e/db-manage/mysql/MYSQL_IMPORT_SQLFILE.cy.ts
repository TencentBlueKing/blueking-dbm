describe('Mysql 变更 SQL 执行 Test', () => {
  beforeEach(() => {
    cy.login();
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'common/listBizs.json',
    }).as('listBizs');
    cy.intercept('get', '/apis/mysql/bizs/3/tendbha_resources/?bk_biz_id=3&limit=10&offset=0', {
      fixture: 'mysql/common/getTendbhaClusters.json',
    }).as('getTendbhaClusters');
    cy.intercept('post', '/apis/mysql/bizs/3/sql_import/semantic_check/', {
      fixture: 'mysql/MYSQL_IMPORT_SQLFILE/semanticCheck.json',
    }).as('semanticCheck');
    cy.intercept('post', '/apis/mysql/bizs/3/sql_import/grammar_check/', {
      fixture: 'mysql/MYSQL_IMPORT_SQLFILE/grammerCheck.json',
    }).as('grammerCheck');
  });

  it('Mysql 变更 SQL 执行', () => {
    cy.on('uncaught:exception', (err) => {
      if (
        ['ResizeObserver', 'false', 'valid user identity', 'Canceled'].some((message) => err.message.includes(message))
      ) {
        return false;
      }
    });
    cy.viewport(1920, 1080);
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_IMPORT_SQLFILE`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('[data-test-id="button_addTargetClusters"]').click();
    cy.wait('@getTendbhaClusters');
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="span_clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="button_clusterSelectorConfirm"]').click();
    cy.get('[data-test-id="button_showExecuteObjects"]').click();
    cy.get('.bk-tag-input').eq(0).click();
    cy.get('.bk-tag-input').find('.tag-input').eq(0).type('test{enter}​').type('{backspace}');
    cy.get('.bk-tag-input').eq(1).click();
    cy.get('.bk-tag-input').find('.tag-input').eq(1).type('hello{enter}​').type('{backspace}');
    cy.get('[data-test-id="div_createFile"]').click();
    cy.wait(500);
    cy.get('.view-line').eq(1).click().type('select * from test;');
    cy.get('[data-test-id="button_grammarCheck"]').click();
    cy.wait('@grammerCheck');
    cy.get('.bk-sideslider-footer').find('button').eq(0).click({ force: true });
    cy.get('[data-test-id="input_ticketRemark"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="button_semanticCheck"]').click();
    cy.wait('@semanticCheck');
    cy.url().should('include', 'log');
  });
});
