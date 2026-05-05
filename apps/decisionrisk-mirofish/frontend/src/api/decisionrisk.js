import service from './index'

export const listDecisionRiskCases = () => service.get('/api/decisionrisk/cases')

export const getDecisionRiskCase = caseId => service.get(`/api/decisionrisk/cases/${caseId}`)

export const getDecisionRiskArtifact = (caseId, artifactName) =>
  service.get(`/api/decisionrisk/cases/${caseId}/artifacts/${artifactName}`)

export const getRiskDocket = caseId =>
  service.get(`/api/decisionrisk/cases/${caseId}/risk-docket`, {
    transformResponse: [data => data]
  })
