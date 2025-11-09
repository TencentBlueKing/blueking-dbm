describe('Mysql 迁移主从 Test', () => {
  beforeEach(() => {
    // @ts-ignore
    cy.login();
    cy.viewport(1920, 1080);
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'mysql/common/listBizs.json',
    }).as('listBizs');
    cy.intercept('post', '/apis/tickets/', {
      fixture: 'mysql/common/ticket.json',
    }).as('submitTicket');
  });

  it('集群迁移-资源池自动匹配', () => {
    cy.on('uncaught:exception', (err, runnable) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_MIGRATE_CLUSTER`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('.db-icon-batch-host-select').click();
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="clusterSelectorConfirmButton"]').click();
    cy.get('[data-test-id="specColumnSelect"]').click();
    const specOptions = cy.get('[data-test-id="specColumnSelect"]').find('.bk-popover').find('.bk-select-option');
    specOptions.should('have.length.above', 0);
    specOptions.last().click({ force: true });
    const resourceTagOptions = cy
      .get('[data-test-id="resourceTagColumnSelect"]')
      .find('.bk-popover')
      .find('.bk-select-option');
    resourceTagOptions.should('have.length.above', 0);
    resourceTagOptions.last().click({ force: true });
    cy.get('[data-test-id="backupSourceRadioGroup"]').find('[type="radio"]').first().check();
    cy.get('[data-test-id="ticketRemarkInput"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="submitTicket"]').click();
    cy.wait('@submitTicket');
    cy.get('.mysql-operation-success-page').should('contain', '任务提交成功');
  });

  it('集群迁移-资源池手动选择', () => {
    cy.on('uncaught:exception', (err, runnable) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_MIGRATE_CLUSTER`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('[data-test-id="sourceTypeRadioGroup"]').find('[type="radio"]').last().check({ force: true });
    cy.get('.db-icon-batch-host-select').click();
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="clusterSelectorConfirmButton"]').click();
    cy.get('[data-test-id="singleResourceHostColumn"]')
      .first()
      .find('[data-test-id="singleResourceHostSelectIcon"]')
      .click();
    cy.get('[data-test-id="resourceHostSelectorRowCheckbox"]').first().click();
    cy.get('[data-test-id="resourceHostSelectorSubmitButton"]').first().click();
    cy.get('[data-test-id="singleResourceHostColumn"]')
      .last()
      .find('[data-test-id="singleResourceHostSelectIcon"]')
      .click();
    cy.get('[data-test-id="resourceHostSelectorRowCheckbox"]').last().click();
    cy.get('[data-test-id="resourceHostSelectorSubmitButton"]').last().click();
    cy.get('[data-test-id="backupSourceRadioGroup"]').find('[type="radio"]').first().check();
    cy.get('[data-test-id="ticketRemarkInput"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="submitTicket"]').click();
    cy.wait('@submitTicket');
    cy.get('.mysql-operation-success-page').should('contain', '任务提交成功');
  });
});
