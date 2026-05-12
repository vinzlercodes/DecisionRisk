<template>
  <main class="decisionrisk-page">
    <header class="page-header">
      <div class="header-row">
        <RouterLink to="/decisionrisk" class="back-link">DecisionRisk</RouterLink>
        <select v-if="runOptions.length" class="run-select" :value="currentRunValue" @change="changeRun">
          <option v-for="run in runOptions" :key="run.execution_id" :value="run.execution_id">
            {{ run.execution_id }} / {{ run.status }} / {{ run.mode }}
          </option>
        </select>
      </div>
      <h1>{{ decisionCase?.title || caseId }}</h1>
      <p>{{ decisionCase?.decision_question || 'DecisionRisk artifact workbench' }}</p>
    </header>

    <section v-if="error" class="status-panel status-panel--bad">
      {{ error }}
    </section>

    <section v-if="audit && !isFinal" class="status-panel status-panel--warn">
      This output is not final. Status: {{ audit.validation_status }}. Any verdict artifact below is shown for audit only.
    </section>

    <section class="summary-bar">
      <div class="summary-item">
        <span>Verdict</span>
        <strong>{{ finalVerdictLabel }}</strong>
      </div>
      <div class="summary-item">
        <span>Recommended option</span>
        <strong>{{ isFinal ? verdict?.recommended_option_id || 'none' : 'not final' }}</strong>
      </div>
      <div class="summary-item">
        <span>Risk pack</span>
        <strong>{{ manifest?.risk_pack || 'unknown' }}</strong>
      </div>
      <div class="summary-item">
        <span>Run mode</span>
        <strong>{{ manifest?.mode || 'unknown' }}</strong>
      </div>
      <div class="summary-item">
        <span>Validation</span>
        <strong>{{ audit?.validation_status || 'unknown' }}</strong>
      </div>
      <div class="summary-item">
        <span>Grounding</span>
        <strong>{{ grounding?.grounding_level || evidenceManifest?.grounding_level || 'unknown' }}</strong>
      </div>
    </section>

    <nav class="tabs" aria-label="DecisionRisk case sections">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-button"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </nav>

    <section v-if="activeTab === 'summary'" class="panel">
      <div class="section-heading">
        <h2>Executive Summary</h2>
        <span>{{ manifest?.created_at || 'No generation timestamp' }}</span>
      </div>
      <div class="verdict-block">
        <strong>{{ finalVerdictLabel }}</strong>
        <p>{{ isFinal ? verdict?.primary_rationale : 'This run has not passed final validation.' }}</p>
      </div>
      <div class="grid-two">
        <div>
          <h3>Required mitigations</h3>
          <ul>
            <li v-for="item in verdict?.required_mitigations || []" :key="item">{{ item }}</li>
            <li v-if="!verdict?.required_mitigations?.length">No mitigation requirements recorded.</li>
          </ul>
        </div>
        <div>
          <h3>Strongest dissent</h3>
          <p>{{ verdict?.strongest_dissent || council?.strongest_dissent || 'No dissent recorded.' }}</p>
        </div>
      </div>
      <div class="callout">
        Raw MiroFish report material is substrate. A final DecisionRisk answer requires Verdict Council output,
        ClaimRefs, and a passing manifest validation.
      </div>
    </section>

    <section v-if="activeTab === 'metrics'" class="panel">
      <div class="section-heading">
        <h2>Option Metrics</h2>
        <span>{{ metrics?.formula_version || 'No formula version' }}</span>
      </div>
      <table v-if="optionRows.length">
        <thead>
          <tr>
            <th>Option</th>
            <th v-for="metric in metricColumns" :key="metric">{{ formatLabel(metric) }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in optionRows" :key="row.option">
            <td>{{ row.option }}</td>
            <td v-for="metric in metricColumns" :key="metric">{{ formatNumber(row.values[metric]) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else>No option metrics artifact is available.</p>
    </section>

    <section v-if="activeTab === 'scenarios'" class="panel">
      <div class="section-heading">
        <h2>Scenario Ensemble</h2>
        <span>{{ scenarioRuns?.runs?.length || 0 }} / {{ scenarioRuns?.expected_runs || 0 }} runs</span>
      </div>
      <div class="filters">
        <label>
          Option
          <select v-model="scenarioFilters.option">
            <option value="">All</option>
            <option v-for="option in scenarioFilterOptions.options" :key="option" :value="option">{{ option }}</option>
          </select>
        </label>
        <label>
          Scenario
          <select v-model="scenarioFilters.scenario">
            <option value="">All</option>
            <option v-for="scenario in scenarioFilterOptions.scenarios" :key="scenario" :value="scenario">{{ scenario }}</option>
          </select>
        </label>
        <label>
          Status
          <select v-model="scenarioFilters.status">
            <option value="">All</option>
            <option v-for="status in scenarioFilterOptions.statuses" :key="status" :value="status">{{ status }}</option>
          </select>
        </label>
      </div>
      <div class="run-grid">
        <article v-for="run in filteredScenarioRuns" :key="run.run_id" class="run-card">
          <strong>{{ run.run_id }}</strong>
          <span>{{ run.option_id }} / {{ run.scenario_id }} / seed {{ run.seed }}</span>
          <span>Status: {{ run.status }}</span>
          <span>ClaimRefs: {{ (run.claim_refs || []).join(', ') || 'none' }}</span>
        </article>
      </div>
    </section>

    <section v-if="activeTab === 'evidence'" class="panel">
      <div class="section-heading">
        <h2>Evidence & ClaimRefs</h2>
        <span>{{ claimRefs.length }} ClaimRefs</span>
      </div>
      <div class="grid-two">
        <div>
          <h3>Evidence</h3>
          <article v-for="item in evidenceManifest?.evidence_items || []" :key="item.evidence_id" class="evidence-row">
            <strong>{{ item.evidence_id }}</strong>
            <span>{{ item.source_type }}</span>
            <code>{{ item.path }}</code>
          </article>
          <p v-if="!evidenceManifest?.evidence_items?.length">No evidence manifest is available.</p>
        </div>
        <div>
          <h3>Grounding</h3>
          <dl class="definition-list">
            <dt>Confidence cap</dt>
            <dd>{{ grounding?.confidence_cap ?? 'unknown' }}</dd>
            <dt>Unsupported assumptions</dt>
            <dd>{{ grounding?.unsupported_assumptions ?? 'unknown' }}</dd>
            <dt>Web grounding</dt>
            <dd>{{ grounding?.web_grounding || 'unknown' }}</dd>
          </dl>
        </div>
      </div>
      <table v-if="claimRefs.length">
        <thead>
          <tr>
            <th>ClaimRef</th>
            <th>Status</th>
            <th>Confidence</th>
            <th>Text</th>
            <th>Sources</th>
            <th>Used in</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="claim in claimRefs" :key="claim.claim_id">
            <td><code>{{ claim.claim_id }}</code></td>
            <td>{{ claim.status }}</td>
            <td>{{ formatNumber(claim.confidence) }}</td>
            <td>{{ claim.text }}</td>
            <td>{{ (claim.source_refs || []).join(', ') || 'none' }}</td>
            <td>{{ (claim.used_in || []).join(', ') || 'none' }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="activeTab === 'council'" class="panel">
      <div class="section-heading">
        <h2>Council Review</h2>
        <span>{{ council?.mode || 'No council mode' }}</span>
      </div>
      <div v-if="council?.gate" class="callout">
        Gate: {{ council.gate.result }}. {{ (council.gate.warnings || []).join(' ') }}
      </div>
      <article v-for="role in council?.role_outputs || []" :key="role.role_id" class="role-card">
        <h3>{{ role.role_name }}</h3>
        <p>{{ role.analysis }}</p>
        <span>Dissent: {{ role.dissent }}</span>
        <span>ClaimRefs: {{ (role.claim_refs || []).join(', ') || 'none' }}</span>
      </article>
      <div v-if="council?.chair_output" class="verdict-block">
        <strong>Chair synthesis</strong>
        <p>{{ council.chair_output.rationale }}</p>
      </div>
    </section>

    <section v-if="activeTab === 'docket'" class="panel docket">
      <div class="section-heading">
        <h2>Risk Docket</h2>
        <a v-if="artifactMap.risk_docket" :href="rawHref(artifactMap.risk_docket.raw_url)" target="_blank">Raw Markdown</a>
      </div>
      <div v-if="docket" class="markdown-body" v-html="renderMarkdown(docket)"></div>
      <p v-else>No Risk Docket artifact is available.</p>
    </section>

    <section v-if="activeTab === 'audit'" class="panel">
      <div class="section-heading">
        <h2>Artifact Audit</h2>
        <span>{{ audit?.validation_result || 'unknown' }}</span>
      </div>
      <dl class="definition-list audit-summary">
        <dt>Source</dt>
        <dd>{{ sourceType }}</dd>
        <dt>Execution</dt>
        <dd>{{ selectedExecutionId || 'flat output' }}</dd>
        <dt>Validation source</dt>
        <dd>{{ audit?.source || 'unknown' }}</dd>
        <dt>Final</dt>
        <dd>{{ audit?.final ? 'yes' : 'no' }}</dd>
      </dl>
      <div v-if="audit?.errors?.length" class="status-panel status-panel--bad">
        <strong>Validation errors</strong>
        <ul>
          <li v-for="item in audit.errors" :key="item">{{ item }}</li>
        </ul>
      </div>
      <table>
        <thead>
          <tr>
            <th>Artifact</th>
            <th>Section</th>
            <th>Path</th>
            <th>Exists</th>
            <th>SHA-256</th>
            <th>Raw</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in artifactRows" :key="item.name">
            <td>{{ item.name }}</td>
            <td>{{ item.section }}</td>
            <td><code>{{ item.path }}</code></td>
            <td>{{ item.exists ? 'yes' : 'no' }}</td>
            <td>
              <code>{{ item.sha256 || 'missing' }}</code>
              <span v-if="item.exists && !item.hash_matches" class="hash-warning">mismatch</span>
            </td>
            <td>
              <a :href="rawHref(item.raw_url)" target="_blank">Open</a>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getDecisionRiskArtifact,
  getDecisionRiskCase,
  getDecisionRiskRun,
  getDecisionRiskRunArtifact,
  getRiskDocket,
  getRunRiskDocket
} from '../../api/decisionrisk'

const route = useRoute()
const router = useRouter()

const tabs = [
  { id: 'summary', label: 'Executive Summary' },
  { id: 'metrics', label: 'Option Metrics' },
  { id: 'scenarios', label: 'Scenario Ensemble' },
  { id: 'evidence', label: 'Evidence & ClaimRefs' },
  { id: 'council', label: 'Council Review' },
  { id: 'docket', label: 'Risk Docket' },
  { id: 'audit', label: 'Artifact Audit' }
]

const artifactNames = [
  'decision_case',
  'verdict',
  'simulation_metrics',
  'grounding_report',
  'scenario_runs',
  'scenario_design',
  'evidence_manifest',
  'council_rounds',
  'mirofish_report_claims'
]

const activeTab = ref('summary')
const loading = ref(false)
const error = ref('')
const manifest = ref(null)
const audit = ref(null)
const artifactMap = ref({})
const runs = ref([])
const selectedExecutionId = ref(null)
const sourceType = ref('flat')
const loadedArtifacts = reactive({})
const docket = ref('')
const scenarioFilters = reactive({ option: '', scenario: '', status: '' })

const caseId = computed(() => String(route.params.caseId || ''))
const routeExecutionId = computed(() => route.params.executionId ? String(route.params.executionId) : '')
const decisionCase = computed(() => loadedArtifacts.decision_case)
const verdict = computed(() => loadedArtifacts.verdict)
const metrics = computed(() => loadedArtifacts.simulation_metrics)
const grounding = computed(() => loadedArtifacts.grounding_report)
const scenarioRuns = computed(() => loadedArtifacts.scenario_runs)
const evidenceManifest = computed(() => loadedArtifacts.evidence_manifest)
const council = computed(() => loadedArtifacts.council_rounds)
const isFinal = computed(() => Boolean(audit.value?.validated && audit.value?.final))
const finalVerdictLabel = computed(() => (isFinal.value ? verdict.value?.final_verdict || 'unknown' : 'not final'))
const runOptions = computed(() => runs.value || [])
const currentRunValue = computed(() => selectedExecutionId.value || '')

const optionRows = computed(() => {
  const options = metrics.value?.options || {}
  return Object.entries(options).map(([option, values]) => ({ option, values }))
})

const metricColumns = computed(() => {
  const first = optionRows.value[0]
  return first ? Object.keys(first.values) : []
})

const scenarioFilterOptions = computed(() => {
  const rows = scenarioRuns.value?.runs || []
  return {
    options: unique(rows.map(run => run.option_id)),
    scenarios: unique(rows.map(run => run.scenario_id)),
    statuses: unique(rows.map(run => run.status))
  }
})

const filteredScenarioRuns = computed(() => {
  return (scenarioRuns.value?.runs || []).filter(run => {
    if (scenarioFilters.option && run.option_id !== scenarioFilters.option) return false
    if (scenarioFilters.scenario && run.scenario_id !== scenarioFilters.scenario) return false
    if (scenarioFilters.status && run.status !== scenarioFilters.status) return false
    return true
  })
})

const claimRefs = computed(() => {
  const byId = new Map()
  Object.values(loadedArtifacts).forEach(value => {
    collectClaimRefs(value).forEach(claim => {
      if (!byId.has(claim.claim_id)) byId.set(claim.claim_id, claim)
    })
  })
  return Array.from(byId.values()).sort((left, right) => String(left.claim_id).localeCompare(String(right.claim_id)))
})

const artifactRows = computed(() => {
  return Object.entries(artifactMap.value || {})
    .map(([name, metadata]) => ({ name, ...metadata }))
    .sort((left, right) => `${left.section}:${left.name}`.localeCompare(`${right.section}:${right.name}`))
})

const loadCase = async () => {
  loading.value = true
  error.value = ''
  try {
    Object.keys(loadedArtifacts).forEach(key => delete loadedArtifacts[key])
    const response = routeExecutionId.value
      ? await getDecisionRiskRun(caseId.value, routeExecutionId.value)
      : await getDecisionRiskCase(caseId.value)

    manifest.value = response.manifest
    audit.value = response.audit
    artifactMap.value = response.artifacts || {}
    runs.value = response.runs || []
    selectedExecutionId.value = response.execution_id || null
    sourceType.value = response.source_type || 'flat'

    await Promise.all(artifactNames.map(loadArtifact))
    docket.value = await loadRiskDocket()
  } catch (err) {
    error.value = err.message || 'Failed to load DecisionRisk case.'
  } finally {
    loading.value = false
  }
}

const loadArtifact = async name => {
  try {
    const response = routeExecutionId.value
      ? await getDecisionRiskRunArtifact(caseId.value, routeExecutionId.value, name)
      : await getDecisionRiskArtifact(caseId.value, name)
    loadedArtifacts[name] = response.artifact
  } catch (err) {
    loadedArtifacts[name] = null
  }
}

const loadRiskDocket = async () => {
  try {
    return routeExecutionId.value
      ? await getRunRiskDocket(caseId.value, routeExecutionId.value)
      : await getRiskDocket(caseId.value)
  } catch (err) {
    return ''
  }
}

const changeRun = event => {
  const executionId = event.target.value
  if (!executionId) return
  router.push({ name: 'DecisionRiskRun', params: { caseId: caseId.value, executionId } })
}

const rawHref = rawUrl => {
  if (!rawUrl) return '#'
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001'
  return rawUrl.startsWith('/api/') ? `${baseUrl}${rawUrl}` : rawUrl
}

const formatLabel = value => String(value).replaceAll('_', ' ')

const formatNumber = value => {
  if (typeof value !== 'number') return value ?? 'unknown'
  return value.toFixed(2)
}

const renderMarkdown = text => {
  const lines = escapeHtml(text || '').split('\n')
  let inList = false
  const html = []
  const closeList = () => {
    if (inList) {
      html.push('</ul>')
      inList = false
    }
  }

  lines.forEach(line => {
    const trimmed = line.trim()
    if (!trimmed) {
      closeList()
      return
    }
    if (trimmed.startsWith('### ')) {
      closeList()
      html.push(`<h3>${trimmed.slice(4)}</h3>`)
    } else if (trimmed.startsWith('## ')) {
      closeList()
      html.push(`<h2>${trimmed.slice(3)}</h2>`)
    } else if (trimmed.startsWith('# ')) {
      closeList()
      html.push(`<h1>${trimmed.slice(2)}</h1>`)
    } else if (trimmed.startsWith('- ')) {
      if (!inList) {
        html.push('<ul>')
        inList = true
      }
      html.push(`<li>${trimmed.slice(2)}</li>`)
    } else {
      closeList()
      html.push(`<p>${trimmed}</p>`)
    }
  })
  closeList()
  return html.join('')
}

const collectClaimRefs = value => {
  const refs = []
  if (Array.isArray(value)) {
    value.forEach(item => refs.push(...collectClaimRefs(item)))
  } else if (value && typeof value === 'object') {
    if (value.claim_id && value.status && value.text) refs.push(value)
    Object.values(value).forEach(child => refs.push(...collectClaimRefs(child)))
  }
  return refs
}

const unique = values => Array.from(new Set(values.filter(Boolean))).sort()

const escapeHtml = value => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;')

onMounted(loadCase)
watch(() => route.fullPath, loadCase)
</script>

<style scoped>
.decisionrisk-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 32px 20px 56px;
  color: #111111;
}

.page-header {
  display: grid;
  gap: 10px;
}

.header-row,
.section-heading,
.filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.back-link {
  color: inherit;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}

.run-select,
.filters select {
  min-height: 34px;
  border: 1px solid #c8ced8;
  background: #ffffff;
  color: #111111;
  font: inherit;
}

.page-header h1 {
  margin: 0;
  font-size: 32px;
  line-height: 1.15;
}

.page-header p {
  max-width: 900px;
  margin: 0;
  color: #555f6d;
}

.summary-bar {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 1px;
  margin-top: 24px;
  border: 1px solid #d8dee4;
  background: #d8dee4;
}

.summary-item {
  min-width: 0;
  padding: 14px;
  background: #ffffff;
}

.summary-item span {
  display: block;
  margin-bottom: 6px;
  color: #667085;
  font-size: 11px;
  text-transform: uppercase;
}

.summary-item strong {
  display: block;
  overflow-wrap: anywhere;
  font-size: 15px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-top: 24px;
  overflow-x: auto;
}

.tab-button {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #d8dee4;
  background: #ffffff;
  color: #111111;
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  white-space: nowrap;
}

.tab-button.active {
  background: #111111;
  border-color: #111111;
  color: #ffffff;
}

.panel,
.status-panel {
  margin-top: 18px;
  padding: 18px;
  border: 1px solid #d8dee4;
  border-radius: 6px;
  background: #ffffff;
}

.status-panel--warn {
  border-color: #f59e0b;
  background: #fffbeb;
}

.status-panel--bad {
  border-color: #dc2626;
  background: #fef2f2;
}

.section-heading {
  margin-bottom: 16px;
}

.section-heading h2,
.role-card h3,
.grid-two h3 {
  margin: 0;
}

.section-heading span,
.section-heading a {
  color: #667085;
  font-size: 13px;
}

.verdict-block,
.callout,
.role-card,
.evidence-row,
.run-card {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f8fafc;
}

.verdict-block strong {
  font-size: 22px;
}

.grid-two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 18px;
}

.filters {
  justify-content: flex-start;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.filters label {
  display: grid;
  gap: 6px;
  color: #667085;
  font-size: 12px;
  text-transform: uppercase;
}

.run-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 10px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}

th {
  color: #667085;
  font-size: 11px;
  text-transform: uppercase;
}

code {
  overflow-wrap: anywhere;
  font-size: 12px;
}

.definition-list {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 8px 14px;
  margin: 0;
}

.definition-list dt {
  color: #667085;
  font-weight: 700;
}

.definition-list dd {
  margin: 0;
}

.audit-summary {
  margin-bottom: 16px;
}

.hash-warning {
  display: block;
  margin-top: 4px;
  color: #b91c1c;
  font-weight: 700;
}

.markdown-body {
  line-height: 1.6;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 18px 0 8px;
}

.markdown-body :deep(p) {
  margin: 0 0 10px;
}

@media (max-width: 900px) {
  .summary-bar,
  .grid-two {
    grid-template-columns: 1fr;
  }

  .header-row,
  .section-heading {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
