describe('Mysql 迁移主从 Test', () => {
  beforeEach(() => {
    cy.login();
    cy.viewport(1920, 1080);
    cy.intercept('get', '/apis/cmdb/list_bizs/', {
      fixture: 'common/listBizs.json',
    }).as('listBizs');
    cy.intercept('post', '/apis/tickets/', {
      fixture: 'common/ticket.json',
    }).as('submitTicket');
  });

  it('集群迁移-资源池自动匹配', () => {
    cy.on('uncaught:exception', (err) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_MIGRATE_CLUSTER`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('.db-icon-batch-host-select').click();
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="span_clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="button_clusterSelectorConfirm"]').click();
    cy.get('[data-test-id="column_spec"]').click();
    const specOptions = cy.get('[data-test-id="column_spec"]').find('.bk-popover').find('.bk-select-option');
    specOptions.should('have.length.above', 0);
    specOptions.last().click({ force: true });
    const resourceTagOptions = cy
      .get('[data-test-id="column_resoureTag"]')
      .find('.bk-popover')
      .find('.bk-select-option');
    resourceTagOptions.should('have.length.above', 0);
    resourceTagOptions.last().click({ force: true });
    cy.get('[data-test-id="form_backupSource"]').find('[type="radio"]').first().check();
    cy.get('[data-test-id="input_ticketRemark"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="button_submitTicket"]').click();
    cy.wait('@submitTicket');
    cy.get('.toolbox-result-success-page').should('contain', '任务提交成功');
  });

  it('集群迁移-资源池手动选择', () => {
    cy.on('uncaught:exception', (err) => {
      if (['ResizeObserver', 'false', 'valid user identity'].some((message) => err.message.includes(message))) {
        return false;
      }
    });
    const url = `${Cypress.env('LOCAL_URL')}/3/db-manage/mysql/toolbox/MYSQL_MIGRATE_CLUSTER`;
    cy.visit(url);
    cy.wait('@listBizs');
    cy.get('[data-test-id="radio_sourceType"]').find('[type="radio"]').last().check({ force: true });
    cy.get('.db-icon-batch-host-select').click();
    cy.get('.vxe-body--row').not('is-offline').first().click();
    cy.get('[data-test-id="span_clusterSelectorPreviewItem"]').should('exist');
    cy.get('[data-test-id="button_clusterSelectorConfirm"]').click();
    cy.get('[data-test-id="column_singleResoureHost"]')
      .first()
      .find('[data-test-id="icon_singleResoureHostSelectIcon"]')
      .click();
    cy.get('[data-test-id="checkbox_resourceHostSelectorRow"]').first().click();
    cy.get('[data-test-id="button_resourceHostSelectorConfirm"]').first().click();
    cy.get('[data-test-id="column_singleResoureHost"]')
      .last()
      .find('[data-test-id="icon_singleResoureHostSelectIcon"]')
      .click();
    cy.get('[data-test-id="checkbox_resourceHostSelectorRow"]').last().click();
    cy.get('[data-test-id="button_resourceHostSelectorConfirm"]').last().click();
    cy.get('[data-test-id="form_backupSource"]').find('[type="radio"]').first().check();
    cy.get('[data-test-id="input_ticketRemark"]').type('前端自动化测试，请忽略此单据');
    cy.get('[data-test-id="button_submitTicket"]').click();
    cy.wait('@submitTicket');
    cy.get('.toolbox-result-success-page').should('contain', '任务提交成功');
  });
});
