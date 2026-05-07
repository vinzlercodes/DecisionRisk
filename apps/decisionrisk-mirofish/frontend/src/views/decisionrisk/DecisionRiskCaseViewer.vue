<template>
  <main class="decisionrisk-page">
    <header class="page-header">
      <RouterLink to="/decisionrisk">DecisionRisk</RouterLink>
      <h1>{{ caseId }}</h1>
      <p v-if="manifest">{{ manifest.risk_pack }} · {{ manifest.mode }} · {{ manifest.created_at }}</p>
      <p v-if="executionId">Execution: {{ executionId }}</p>
    </header>

    <section v-if="verdict" class="panel verdict">
      <h2>Verdict</h2>
      <strong>{{ verdict.final_verdict }}</strong>
      <p>{{ verdict.primary_rationale }}</p>
      <p>Recommended option: {{ verdict.recommended_option_id || 'none' }}</p>
      <p>Confidence: {{ verdict.confidence }}</p>
    </section>

    <section v-if="metrics" class="panel">
      <h2>Option Comparison</h2>
      <table>
        <thead>
          <tr>
            <th>Option</th>
            <th>Risk</th>
            <th>Backlash</th>
            <th>Trust damage</th>
            <th>Regulator attention</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, option) in metrics.options" :key="option">
            <td>{{ option }}</td>
            <td>{{ row.overall_risk_score }}</td>
            <td>{{ row.backlash_intensity }}</td>
            <td>{{ row.trust_damage }}</td>
            <td>{{ row.regulator_attention }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="grounding" class="panel">
      <h2>Grounding</h2>
      <p>Level: {{ grounding.grounding_level }}</p>
      <p>Evidence items: {{ grounding.evidence_items }}</p>
      <p>Unsupported assumptions: {{ grounding.unsupported_assumptions }}</p>
    </section>

    <section v-if="runs" class="panel">
      <h2>Scenario Ensemble</h2>
      <p>{{ runs.runs.length }} replay runs</p>
    </section>

    <section v-if="council" class="panel">
      <h2>Council</h2>
      <p>{{ council.strongest_dissent }}</p>
    </section>

    <section v-if="docket" class="panel docket">
      <h2>Risk Docket</h2>
      <pre>{{ docket }}</pre>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getDecisionRiskArtifact, getDecisionRiskCase, getRiskDocket } from '../../api/decisionrisk'

const route = useRoute()
const caseId = route.params.caseId
const executionId = route.query.execution_id || ''
const manifest = ref(null)
const verdict = ref(null)
const metrics = ref(null)
const grounding = ref(null)
const runs = ref(null)
const council = ref(null)
const docket = ref('')

const loadArtifact = async name => {
  const response = await getDecisionRiskArtifact(caseId, name, executionId)
  return response.artifact
}

onMounted(async () => {
  const response = await getDecisionRiskCase(caseId, executionId)
  manifest.value = response.manifest
  ;[verdict.value, metrics.value, grounding.value, runs.value, council.value] = await Promise.all([
    loadArtifact('verdict'),
    loadArtifact('simulation_metrics'),
    loadArtifact('grounding_report'),
    loadArtifact('scenario_runs'),
    loadArtifact('council_rounds')
  ])
  docket.value = await getRiskDocket(caseId, executionId)
})
</script>

<style scoped>
.decisionrisk-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 20px;
}

.page-header h1 {
  margin: 8px 0;
}

.panel {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid #d8dee4;
  border-radius: 6px;
}

.verdict strong {
  font-size: 24px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 8px;
  border-bottom: 1px solid #d8dee4;
  text-align: left;
}

.docket pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
