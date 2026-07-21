import type { PolicyRule } from '../types/rbac'

export class RbacYamlError extends Error {}

function asStringArray(value: unknown, field: string, ruleIndex: number): string[] {
  if (value === undefined || value === null) return []
  if (typeof value === 'string') return [value]
  if (Array.isArray(value) && value.every((v) => typeof v === 'string')) return value
  throw new RbacYamlError(`Rule ${ruleIndex + 1}: "${field}" must be a string or a list of strings`)
}

/**
 * Accepts either a bare `rules:` array (as copy-pasted from a manifest) or a
 * full Role/ClusterRole manifest with a top-level `rules:` key. js-yaml is
 * loaded on demand — this is a rarely-used path, no reason to ship it in the
 * main bundle.
 */
export async function parseRulesYaml(text: string): Promise<PolicyRule[]> {
  const { load } = await import('js-yaml')

  let parsed: unknown
  try {
    parsed = load(text)
  } catch (e) {
    throw new RbacYamlError(e instanceof Error ? `Invalid YAML: ${e.message}` : 'Invalid YAML')
  }

  const rulesValue = Array.isArray(parsed)
    ? parsed
    : parsed && typeof parsed === 'object' && Array.isArray((parsed as Record<string, unknown>).rules)
      ? (parsed as Record<string, unknown>).rules
      : null

  if (!Array.isArray(rulesValue)) {
    throw new RbacYamlError('Expected a list of rules, or an object with a "rules:" array')
  }
  if (rulesValue.length === 0) {
    throw new RbacYamlError('No rules found')
  }

  return rulesValue.map((entry, i) => {
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new RbacYamlError(`Rule ${i + 1} must be a mapping (apiGroups/resources/verbs)`)
    }
    const r = entry as Record<string, unknown>
    const apiGroups = asStringArray(r.apiGroups ?? r.api_groups, 'apiGroups', i)
    const resources = asStringArray(r.resources, 'resources', i)
    const verbs = asStringArray(r.verbs, 'verbs', i)
    const resourceNames = asStringArray(r.resourceNames ?? r.resource_names, 'resourceNames', i)

    if (verbs.length === 0) {
      throw new RbacYamlError(`Rule ${i + 1}: "verbs" is required`)
    }

    const rule: PolicyRule = {
      // Empty apiGroups (or [""]) means the core API group — keep that shape
      api_groups: apiGroups.length ? apiGroups : [''],
      resources,
      verbs,
    }
    if (resourceNames.length) rule.resource_names = resourceNames
    return rule
  })
}
