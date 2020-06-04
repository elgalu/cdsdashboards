
it('voila dashboard', () => {
  
  do_login()

  cy.get('#thenavbar > ul:nth-child(1) > li:nth-child(4) > a')
    .should('contain', 'Dashboards').click()

  cy.get('#start')
    .should('contain', 'New Dashboard').click()

  cy.get('#main > div > div > form > p:nth-child(2) > input[type=text]')
    .type('Voila Test')

  cy.get('#main > div > div > form > p:nth-child(12) > input[type=text]')
    .type('Test.ipynb')

  cy.get('#main > div > div > form > div > input[type=submit]')
    .click()

  cy.get('#launch').should('contain', 'Go to Dashboard')
    .click()

  cy.get('#rendered_cells > main > div > div > div > div > div:nth-child(3) > div > div > div > div > pre')
    .should('contain', 'test')

})

