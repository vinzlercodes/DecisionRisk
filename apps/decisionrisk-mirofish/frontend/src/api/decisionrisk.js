import service from './index'

export const listDecisionRiskCases = () => service.get('/api/decisionrisk/cases')

export const listDecisionRiskRuntimeModes = () => service.get('/api/decisionrisk/runtime-modes')

export const createDecisionRiskRun = payload => service.post('/api/decisionrisk/runs', payload)

export const getDecisionRiskCase = (caseId, executionId) =>
  service.get(`/api/decisionrisk/cases/${caseId}`, {
    params: executionId ? { execution_id: executionId } : {}
  })

export const getDecisionRiskArtifact = (caseId, artifactName, executionId) =>
  service.get(`/api/decisionrisk/cases/${caseId}/artifacts/${artifactName}`, {
    params: executionId ? { execution_id: executionId } : {}
  })

export const getRiskDocket = (caseId, executionId) =>
  service.get(`/api/decisionrisk/cases/${caseId}/risk-docket`, {
    params: executionId ? { execution_id: executionId } : {},
    transformResponse: [data => data]
  })
