describe('Recruiter Dashboard', () => {

  it('opens dashboard', () => {
    cy.visit('http://localhost:3000')

    cy.contains('Overview').should('be.visible')
  })

  it('opens Candidates page', () => {
    cy.visit('http://localhost:3000')

    cy.contains('Candidates').click()

    cy.contains('Candidate profiles').should('be.visible')
  })

  it('opens Sessions page', () => {
    cy.visit('http://localhost:3000')

    cy.contains('Sessions').click()

    cy.contains('Sessions').should('be.visible')
  })

})