import TicketSuccess from '../../src/components/ticket-success/Index.vue';

describe('<TicketSuccess />', () => {
  it('renders', () => {
    // @ts-ignore
    cy.mount(TicketSuccess, {
      props: {
        steps: [
          {
            name: '111',
          },
          {
            name: '222',
          },
        ],
      },
    });
    cy.get('.operation-steps').children().should('have.length', 2);
    cy.get('.operation-steps').children().eq(0).find('.status-loading').should('exist');
    cy.get('.operation-steps').children().eq(0).should('have.text', '111');
    cy.get('.operation-steps').children().eq(1).should('have.text', '222');
  });
});
