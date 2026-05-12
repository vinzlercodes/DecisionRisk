<template>
  <main class="decisionrisk-page">
    <header class="page-header">
      <h1>DecisionRisk</h1>
      <p>Replay-first risk dockets generated from DecisionRisk artifacts.</p>
    </header>

    <section class="case-list">
      <RouterLink
        v-for="item in cases"
        :key="item.case_id"
        class="case-row"
        :to="`/decisionrisk/${item.case_id}`"
      >
        <strong>{{ item.case_id }}</strong>
        <span>{{ item.risk_pack }}</span>
        <span>{{ item.mode }}</span>
        <span>{{ item.validation_status }}</span>
      </RouterLink>
    </section>
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listDecisionRiskCases } from '../../api/decisionrisk'

const cases = ref([])

onMounted(async () => {
  const response = await listDecisionRiskCases()
  cases.value = response.cases || []
})
</script>

<style scoped>
.decisionrisk-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: 32px 20px;
}

.page-header h1 {
  margin: 0 0 8px;
}

.case-list {
  display: grid;
  gap: 8px;
  margin-top: 24px;
}

.case-row {
  display: grid;
  grid-template-columns: 1fr 160px 120px 140px;
  gap: 16px;
  padding: 12px;
  border: 1px solid #d8dee4;
  border-radius: 6px;
  color: inherit;
  text-decoration: none;
}
</style>
