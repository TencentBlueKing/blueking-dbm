/// <reference types="cypress" />
// ***********************************************
// This example commands.ts shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })
//
declare global {
  namespace Cypress {
    interface Chainable {
      login(): void;
    }
  }
}

// Cypress.Commands.add('login', () => {
//   // 使用 cy.session() 缓存登录会话
//   cy.session('login', () => {
//     // 这里是执行登录操作的代码
//     const loginUrl = Cypress.env('LOGIN_URL');
//     const username = Cypress.env('USERNAME');
//     const password = Cypress.env('PASSWORD');
//     cy.visit(loginUrl);
//     cy.get('[name="username"]').type(username);
//     cy.get('[name="password"]').type(password);
//     cy.get('#login-btn').click();
//     cy.url().should('contain', 'local');
//   });
// });

Cypress.Commands.add('login', () => {
  // 缓存登录会话
  cy.session('login', () => {
    cy.setCookie('dbm_csrftoken', Cypress.env('dbm_csrftoken'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
    cy.setCookie('dbm_sessionid', Cypress.env('dbm_sessionid'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
    cy.setCookie('bk_ticket', Cypress.env('bk_ticket'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('bk_uid', Cypress.env('bk_uid'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('blueking_language', Cypress.env('blueking_language'), {
      domain: Cypress.env('ROOT_DOMAIN'),
      path: '/',
    });
    cy.setCookie('DiggerTraceId', Cypress.env('DiggerTraceId'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('DiggerTraceIdTs', Cypress.env('DiggerTraceIdTs'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('ERP_USERNAME', Cypress.env('ERP_USERNAME'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('pgv_info', Cypress.env('pgv_info'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('pgv_pvid', Cypress.env('pgv_pvid'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('RIO_TOKEN', Cypress.env('RIO_TOKEN'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('sensorsdata2015jssdkcross', Cypress.env('sensorsdata2015jssdkcross'), {
      domain: Cypress.env('ROOT_DOMAIN'),
      path: '/',
    });
    cy.setCookie('wsd_ulog', Cypress.env('wsd_ulog'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('x_host_key_access', Cypress.env('x_host_key_access'), {
      domain: Cypress.env('ROOT_DOMAIN'),
      path: '/',
    });
    cy.setCookie('x-client-ssid', Cypress.env('x-client-ssid'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('x-mp-host-key', Cypress.env('x-mp-host-key'), { domain: Cypress.env('ROOT_DOMAIN'), path: '/' });
    cy.setCookie('bk_token', Cypress.env('bk_token'), { domain: Cypress.env('PAASDB_DOMAIN'), path: '/' });
    cy.setCookie('blueking_language', Cypress.env('blueking_language'), {
      domain: Cypress.env('PAASDB_DOMAIN'),
      path: '/',
    });
  });

  // PO环境
  // cy.session('login', () => {
  //   cy.setCookie('_t_uid', Cypress.env('_t_uid'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
  //   cy.setCookie('yyb_muid', Cypress.env('yyb_muid'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
  //   cy.setCookie('bk_token', Cypress.env('bk_token'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
  //   cy.setCookie('blueking_language', Cypress.env('blueking_language'), {
  //     domain: Cypress.env('BKDBM_DOMAIN'),
  //     path: '/',
  //   });
  //   cy.setCookie('dbm_csrftoken', Cypress.env('dbm_csrftoken'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
  //   cy.setCookie('dbm_sessionid', Cypress.env('dbm_sessionid'), { domain: Cypress.env('BKDBM_DOMAIN'), path: '/' });
  // });
});
