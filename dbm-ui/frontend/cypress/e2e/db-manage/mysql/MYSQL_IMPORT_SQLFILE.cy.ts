describe('Mysql 变更 SQL 执行 Test', () => {
  beforeEach(() => {
    // @ts-ignore
    cy.login();
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'mysql/common/listBizs.json',
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
    cy.on('uncaught:exception', (err, runnable) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    cy.viewport(1920, 1080);
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_IMPORT_SQLFILE`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('[data-test-id="addTargetClustersBtn"]').click();
    cy.wait('@getTendbhaClusters');
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="clusterSelectorConfirmButton"]').click();
    cy.get('[data-test-id="addSqlContentBtn"]').click();
    cy.get('.bk-tag-input').eq(0).click();
    cy.get('.bk-tag-input').find('.tag-input').eq(0).type('test{enter}​').type('{backspace}');
    cy.get('.bk-tag-input').eq(1).click();
    cy.get('.bk-tag-input').find('.tag-input').eq(1).type('hello{enter}​').type('{backspace}');
    cy.get('[data-test-id="manualAddSqlBtn"]').click();
    cy.wait(500);
    cy.get('.view-line').eq(1).click().type('select * from test;');
    cy.get('[data-test-id="manualGrammarCheckBtn"]').click();
    cy.wait('@grammerCheck');
    cy.get('.bk-sideslider-footer').find('button').eq(0).click({ force: true });
    cy.get('[data-test-id="ticketRemarkInput"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="simulationExecuteBtn"]').click();
    cy.wait('@semanticCheck');
    cy.url().should('include', 'log');
  });
});
