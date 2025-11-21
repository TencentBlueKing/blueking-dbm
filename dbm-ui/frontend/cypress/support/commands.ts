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
// declare global {
//   namespace Cypress {
//     interface Chainable {
//       login(email: string, password: string): Chainable<void>
//       drag(subject: string, options?: Partial<TypeOptions>): Chainable<Element>
//       dismiss(subject: string, options?: Partial<TypeOptions>): Chainable<Element>
//       visit(originalFn: CommandOriginalFn, url: string, options: Partial<VisitOptions>): Chainable<Element>
//     }
//   }
// }

// Cypress.Commands.add('login' as any, () => {
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

Cypress.Commands.add('login' as any, () => {
  // 缓存登录会话
  cy.session('login', () => {
    cy.setCookie('dbm_csrftoken', Cypress.env('dbm_csrftoken'), { path: '/', domain: Cypress.env('BKDBM_DOMAIN') });
    cy.setCookie('dbm_sessionid', Cypress.env('dbm_sessionid'), { path: '/', domain: Cypress.env('BKDBM_DOMAIN') });
    cy.setCookie('bk_ticket', Cypress.env('bk_ticket'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('bk_uid', Cypress.env('bk_uid'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('blueking_language', Cypress.env('blueking_language'), {
      path: '/',
      domain: Cypress.env('ROOT_DOMAIN'),
    });
    cy.setCookie('DiggerTraceId', Cypress.env('DiggerTraceId'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('DiggerTraceIdTs', Cypress.env('DiggerTraceIdTs'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('ERP_USERNAME', Cypress.env('ERP_USERNAME'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('pgv_info', Cypress.env('pgv_info'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('pgv_pvid', Cypress.env('pgv_pvid'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('RIO_TOKEN', Cypress.env('RIO_TOKEN'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('sensorsdata2015jssdkcross', Cypress.env('sensorsdata2015jssdkcross'), {
      path: '/',
      domain: Cypress.env('ROOT_DOMAIN'),
    });
    cy.setCookie('wsd_ulog', Cypress.env('wsd_ulog'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('x_host_key_access', Cypress.env('x_host_key_access'), {
      path: '/',
      domain: Cypress.env('ROOT_DOMAIN'),
    });
    cy.setCookie('x-client-ssid', Cypress.env('x-client-ssid'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('x-mp-host-key', Cypress.env('x-mp-host-key'), { path: '/', domain: Cypress.env('ROOT_DOMAIN') });
    cy.setCookie('bk_token', Cypress.env('bk_token'), { path: '/', domain: Cypress.env('PAASDB_DOMAIN') });
    cy.setCookie('blueking_language', Cypress.env('blueking_language'), {
      path: '/',
      domain: Cypress.env('PAASDB_DOMAIN'),
    });
  });
});
