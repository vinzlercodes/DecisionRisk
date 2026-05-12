<template>
  <RouterLink class="decisionrisk-nav-link" to="/decisionrisk">
    {{ $t('nav.decisionrisk') }}
  </RouterLink>
</template>

<style scoped>
.decisionrisk-nav-link {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid currentColor;
  color: inherit;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-decoration: none;
  text-transform: uppercase;
  white-space: nowrap;
}

.decisionrisk-nav-link:hover {
  background: #000000;
  border-color: #000000;
  color: #ffffff;
}
</style>
