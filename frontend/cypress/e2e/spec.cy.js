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

  it('allows language selection and posts selected language when starting interview', () => {
    cy.visit('http://localhost:3000/interview', {
      onBeforeLoad(win) {
        win.localStorage.setItem('api_token', 'fake-token');
        const fakeStream = {
          getTracks: () => [],
          getAudioTracks: () => [],
          getVideoTracks: () => [],
        };
        win.navigator.mediaDevices = {
          getUserMedia: cy.stub().resolves(fakeStream),
        };
        win.AudioContext = class {
          constructor() {}
          createMediaStreamSource() {
            return { connect: () => {} };
          }
          createAnalyser() {
            return {
              fftSize: 64,
              frequencyBinCount: 32,
              getByteFrequencyData: () => {},
            };
          }
          close() {}
        };
      },
    })

    cy.contains('Language').should('be.visible')
    cy.get('select[name="interview-language"]').should('have.value', 'en')
    cy.get('select[name="interview-language"]').select('French')
    cy.get('input[placeholder="cand-1234"]').type('cand-1234')

    cy.intercept('POST', '**/start-interview', (req) => {
      expect(req.body).to.deep.equal({
        candidate_id: 'cand-1234',
        priority: 'high',
        language: 'fr',
      });
      req.reply({ session_id: 'session-1' });
    }).as('startInterview')

    cy.contains('button', 'Start Interview').should('not.be.disabled').click()
    cy.wait('@startInterview')
  })

})