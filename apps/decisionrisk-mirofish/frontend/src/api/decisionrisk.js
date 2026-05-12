import service from './index'

export const listDecisionRiskCases = () => service.get('/api/decisionrisk/cases')

export const listDecisionRiskRuntimeModes = () => service.get('/api/decisionrisk/runtime-modes')

export const createDecisionRiskRun = payload => service.post('/api/decisionrisk/runs', payload)

export const getDecisionRiskCase = caseId => service.get(`/api/decisionrisk/cases/${caseId}`)

export const listDecisionRiskRuns = caseId => service.get(`/api/decisionrisk/cases/${caseId}/runs`)

export const getDecisionRiskRun = (caseId, executionId) =>
  service.get(`/api/decisionrisk/cases/${caseId}/runs/${executionId}`)

export const getDecisionRiskArtifact = (caseId, artifactName) =>
  service.get(`/api/decisionrisk/cases/${caseId}/artifacts/${artifactName}`)

export const getDecisionRiskRunArtifact = (caseId, executionId, artifactName) =>
  service.get(`/api/decisionrisk/cases/${caseId}/runs/${executionId}/artifacts/${artifactName}`)

export const getRiskDocket = caseId =>
  service.get(`/api/decisionrisk/cases/${caseId}/risk-docket`, {
    transformResponse: [data => data]
  })

export const getRunRiskDocket = (caseId, executionId) =>
  service.get(`/api/decisionrisk/cases/${caseId}/runs/${executionId}/risk-docket`, {
    transformResponse: [data => data]
  })
